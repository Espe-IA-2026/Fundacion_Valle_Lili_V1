"""Crawler web que extrae páginas públicas y las convierte al esquema ``RawPage``."""

from __future__ import annotations

import logging
import re
from html.parser import HTMLParser
from typing import TYPE_CHECKING
from urllib.parse import urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup
from markdownify import markdownify as md
from pydantic import AnyHttpUrl, TypeAdapter

from semantic_layer_fvl.config import Settings, get_settings
from semantic_layer_fvl.extractors.http_client import HttpClient
from semantic_layer_fvl.extractors.robots import RobotsPolicy
from semantic_layer_fvl.schemas import ExtractionMetadata, RawPage

if TYPE_CHECKING:
    from semantic_layer_fvl.domains import DomainConfig

_DOMAIN_NOISE_SELECTOR = (
    "nav, footer, header, aside, script, style, noscript, iframe, hr, "
    "figure, svg, img, "
    ".cnt_breadcrumbs, .social-share, "
    ".elementor-location-header, .elementor-location-footer"
)

logger = logging.getLogger(__name__)

_HTTP_URL_ADAPTER = TypeAdapter(AnyHttpUrl)

_NON_HTML_EXTENSIONS = frozenset(
    {
        ".pdf",
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".svg",
        ".webp",
        ".ico",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        ".zip",
        ".rar",
        ".tar",
        ".gz",
        ".mp3",
        ".mp4",
        ".avi",
        ".mov",
        ".wmv",
        ".css",
        ".js",
        ".json",
        ".xml",
        ".rss",
        ".atom",
    }
)

_NOISE_MARKDOWN_LINES = {
    "agenda una cita",
    "autorizo",
    "conoce más",
    "contáctanos",
    "contactanos",
    "descubre aquí",
    "directorio médico",
    "mostrar todos",
    "realizar pagos",
    "solicitar cita por whatsapp",
    "solicitar una llamada",
    "scroll",
    "ver especialidad",
    "ver más recomendados",
    "ver todos los servicios y especialidades",
    "¿cómo llegar?",
}


class CrawlBlockedError(RuntimeError):
    """Se lanza cuando una URL está bloqueada por las reglas del ``robots.txt``."""


class _MetadataParser(HTMLParser):
    """Parser HTML liviano que extrae el título y la meta descripción de una página."""

    def __init__(self) -> None:
        super().__init__()
        self._inside_title = False
        self.title_parts: list[str] = []
        self.meta_description: str | None = None
        self.og_title: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.lower()
        if lowered == "title":
            self._inside_title = True
            return
        if lowered != "meta":
            return

        attr_map = {key.lower(): value for key, value in attrs if value is not None}
        name = attr_map.get("name", "").lower()
        prop = attr_map.get("property", "").lower()
        content = attr_map.get("content")

        if content and prop == "og:title" and self.og_title is None:
            self.og_title = content.strip()

        if content and (name == "description" or prop == "og:description"):
            if self.meta_description is None:
                self.meta_description = content.strip()

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._inside_title = False

    def handle_data(self, data: str) -> None:
        if self._inside_title:
            cleaned = data.strip()
            if cleaned:
                self.title_parts.append(cleaned)


class _TextParser(HTMLParser):
    """Parser HTML que extrae el texto visible de una página, priorizando el contenido principal."""

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.primary_parts: list[str] = []
        self._ignored_depth = 0
        self._ignored_tags = {"head", "script", "style", "noscript", "svg", "title"}
        self._primary_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.lower()
        if lowered in self._ignored_tags:
            self._ignored_depth += 1
            return

        attr_map = {key.lower(): value for key, value in attrs if value is not None}
        if lowered in {"main", "article"} or attr_map.get("role", "").lower() == "main":
            self._primary_depth += 1

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered in self._ignored_tags and self._ignored_depth > 0:
            self._ignored_depth -= 1
            return

        if lowered in {"main", "article"} and self._primary_depth > 0:
            self._primary_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._ignored_depth > 0:
            return
        cleaned = " ".join(data.split())
        if cleaned:
            self.parts.append(cleaned)
            if self._primary_depth > 0:
                self.primary_parts.append(cleaned)


def extract_title(html: str) -> str | None:
    """Extrae el título normalizado de una página HTML, priorizando ``og:title``.

    Args:
        html: Contenido HTML de la página.

    Returns:
        Título normalizado, o ``None`` si no se encontró.
    """
    parser = _MetadataParser()
    parser.feed(html)
    if parser.og_title:
        return normalize_title(parser.og_title)
    if not parser.title_parts:
        return None
    return normalize_title(" ".join(parser.title_parts))


def extract_meta_description(html: str) -> str | None:
    """Extrae la meta descripción (``description`` u ``og:description``) del HTML.

    Args:
        html: Contenido HTML de la página.

    Returns:
        Texto de la meta descripción, o ``None`` si no se encontró.
    """
    parser = _MetadataParser()
    parser.feed(html)
    return parser.meta_description


def decode_html(response) -> str:
    """Decodifica el cuerpo de una respuesta HTTP como texto HTML.

    Intenta las codificaciones en el siguiente orden: cabecera ``Content-Type``,
    meta charset en el HTML, y finalmente UTF-8, CP1252 y Latin-1 como respaldo.

    Args:
        response: Objeto de respuesta ``httpx`` con atributos ``content`` y ``headers``.

    Returns:
        Contenido HTML decodificado como cadena de texto.
    """
    content = response.content
    content_type = response.headers.get("content-type", "")

    encodings: list[str] = []
    charset_match = re.search(r"charset=([A-Za-z0-9._-]+)", content_type, re.IGNORECASE)
    if charset_match:
        encodings.append(charset_match.group(1).strip("\"'"))

    head_snippet = content[:4096].decode("latin-1", errors="ignore")
    meta_match = re.search(
        r"<meta[^>]+charset=['\"]?([A-Za-z0-9._-]+)",
        head_snippet,
        re.IGNORECASE,
    )
    if meta_match:
        encodings.append(meta_match.group(1))

    encodings.extend(["utf-8", "cp1252", "latin-1"])

    tried: set[str] = set()
    for encoding in encodings:
        normalized = encoding.lower()
        if normalized in tried:
            continue
        tried.add(normalized)
        try:
            return content.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue

    return response.text


def extract_text_content(html: str) -> tuple[str, bool]:
    """Extrae el contenido textual visible de una página HTML.

    Prioriza el texto dentro de elementos ``<main>``, ``<article>`` o con
    ``role="main"``; si no los encuentra, utiliza todo el texto visible de la página.

    Args:
        html: Contenido HTML de la página.

    Returns:
        Tupla ``(texto, tiene_contenido_principal)`` donde el segundo elemento indica
        si se encontró un bloque de contenido principal.
    """
    parser = _TextParser()
    parser.feed(html)
    has_primary = bool(parser.primary_parts)
    preferred_parts = parser.primary_parts if has_primary else parser.parts
    return "\n".join(preferred_parts), has_primary


class _LinkParser(HTMLParser):
    """Parser HTML que extrae y normaliza los enlaces internos de una página."""

    def __init__(self, base_url: str) -> None:
        super().__init__()
        self._base_url = base_url
        self._base_domain = urlsplit(base_url).netloc.lower()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        for name, value in attrs:
            if name.lower() == "href" and value:
                link = self._normalize(value.strip())
                if link is not None:
                    self.links.append(link)

    def _normalize(self, href: str) -> str | None:
        if href.startswith(("#", "mailto:", "tel:", "javascript:")):
            return None
        absolute = urljoin(self._base_url, href)
        parts = urlsplit(absolute)
        if parts.scheme not in {"http", "https"}:
            return None
        if parts.netloc.lower() != self._base_domain:
            return None
        path_lower = parts.path.lower()
        # Skip non-Spanish language variants
        if path_lower == "/en" or path_lower.startswith("/en/"):
            return None
        for ext in _NON_HTML_EXTENSIONS:
            if path_lower.endswith(ext):
                return None
        path = parts.path.rstrip("/") or "/"
        return urlunsplit((parts.scheme, parts.netloc, path, "", ""))


def extract_links(html: str, base_url: str) -> list[str]:
    """Extrae los enlaces internos únicos de un HTML, normalizados y filtrados.

    Devuelve URLs absolutas del mismo dominio que ``base_url``, sin fragmentos,
    cadenas de consulta ni extensiones de recursos no HTML.

    Args:
        html: Contenido HTML de la página origen.
        base_url: URL base para resolver rutas relativas y validar el dominio.

    Returns:
        Lista ordenada de URLs internas únicas.
    """
    parser = _LinkParser(base_url)
    parser.feed(html)
    return list(dict.fromkeys(parser.links))


def _normalize_markdown_lines(markdown_content: str) -> str:
    """Elimina líneas de ruido y normaliza los espacios en blanco de un texto Markdown."""
    lines: list[str] = []
    for raw_line in markdown_content.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped == "---":
            if lines and lines[-1] != "":
                lines.append("")
            continue
        if stripped.casefold() in _NOISE_MARKDOWN_LINES:
            continue
        lines.append(line)

    while lines and lines[-1] == "":
        lines.pop()

    return "\n".join(lines).strip()


def _render_specialist_entries(section_body: str) -> list[str]:
    """Convierte el cuerpo Markdown de una sección de especialistas en una lista de entradas limpias."""
    entries: list[str] = []
    link_pattern = re.compile(r"\[(.*?)\]\((https?://[^)]+)\)", re.DOTALL)

    for match in link_pattern.finditer(section_body):
        label = match.group(1)
        parts = [part.strip() for part in re.split(r"\r?\n+", label) if part.strip()]
        cleaned_parts: list[str] = []
        for part in parts:
            if part.startswith("####"):
                cleaned_parts.append(part[4:].strip())
            else:
                cleaned_parts.append(part)

        if not cleaned_parts:
            continue

        name = cleaned_parts[0]
        specialty = cleaned_parts[1] if len(cleaned_parts) > 1 else ""
        entry = f"- {name} - {specialty}" if specialty else f"- {name}"
        entries.append(entry.rstrip(" -"))

    return entries


def _reformat_specialists_section(markdown_content: str, heading: str) -> str:
    """Reformatea la sección de especialistas en el Markdown, reemplazando los enlaces por una lista limpia."""
    pattern = re.compile(
        rf"(?ms)^{re.escape(heading)}\s*(.*?)(?=^#{{1,6}}\s|\Z)",
    )
    match = pattern.search(markdown_content)
    if match is None:
        return markdown_content

    entries = _render_specialist_entries(match.group(1))
    if not entries:
        return markdown_content[: match.start()] + heading + "\n"

    replacement = heading + "\n\n" + "\n".join(entries) + "\n"
    return (
        markdown_content[: match.start()]
        + replacement
        + markdown_content[match.end() :]
    )


def _cut_markdown_at_headings(markdown_content: str, headings: list[str]) -> str:
    """Trunca el Markdown en el primer encabezado coincidente de la lista de corte."""
    if not headings:
        return markdown_content

    earliest_index: int | None = None
    for heading in headings:
        heading_pattern = re.compile(rf"(?im)^\s*{re.escape(heading)}\s*$")
        match = heading_pattern.search(markdown_content)
        if match is None:
            continue
        if earliest_index is None or match.start() < earliest_index:
            earliest_index = match.start()

    if earliest_index is None:
        return markdown_content

    return markdown_content[:earliest_index].rstrip()


def _trim_before_first_h1(markdown_content: str) -> str:
    """Elimina el contenido previo al primer encabezado H1 del Markdown."""
    match = re.search(r"(?m)^#\s+", markdown_content)
    if match is None:
        return markdown_content
    return markdown_content[match.start() :].lstrip()


def _clean_domain_markdown(markdown_content: str, config: DomainConfig) -> str:
    """Aplica el conjunto completo de transformaciones de limpieza Markdown para un dominio dado."""
    cleaned = markdown_content.replace("\r\n", "\n").replace("\r", "\n")
    if config.trim_before_first_h1:
        cleaned = _trim_before_first_h1(cleaned)
    if config.specialists_section_heading:
        cleaned = _reformat_specialists_section(
            cleaned, config.specialists_section_heading
        )
    cleaned = _cut_markdown_at_headings(cleaned, config.markdown_cutoff_headings)
    cleaned = _normalize_markdown_lines(cleaned)
    return cleaned


def normalize_title(value: str) -> str:
    """Normaliza un título de página eliminando el sufijo de sitio y espacios redundantes.

    Args:
        value: Título crudo extraído del HTML.

    Returns:
        Título limpio sin sufijo tras ``|`` ni espacios innecesarios.
    """
    normalized = re.sub(r"\s+", " ", value).strip()
    normalized = re.sub(r"([a-záéíóúñ])([A-ZÁÉÍÓÚÑ])", r"\1 \2", normalized)

    if "|" in normalized:
        first_part = normalized.split("|")[0].strip()
        if len(first_part) > 5:
            return first_part

    return normalized


class WebCrawler:
    """Crawler minimalista que obtiene páginas públicas y las convierte al esquema ``RawPage``."""

    def __init__(
        self,
        client: HttpClient | None = None,
        *,
        settings: Settings | None = None,
        robots_policy: RobotsPolicy | None = None,
        source_name: str = "Fundacion Valle del Lili",
    ) -> None:
        """Inicializa el crawler con dependencias inyectables.

        Args:
            client: Cliente HTTP a utilizar. Si es ``None`` se crea uno con ``settings``.
            settings: Configuración del proyecto. Si es ``None`` se obtiene la instancia global.
            robots_policy: Política de ``robots.txt`` a usar. Si es ``None`` se crea una nueva.
            source_name: Nombre legible de la fuente para los metadatos de extracción.
        """
        self.settings = settings or get_settings()
        self.client = client or HttpClient(self.settings)
        self.robots_policy = robots_policy or RobotsPolicy(self.settings.user_agent)
        self.source_name = source_name

    _BROWSER_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
    }

    def fetch_domain_page(
        self, url: str | AnyHttpUrl, config: DomainConfig
    ) -> RawPage | None:
        """Obtiene una página usando el selector CSS del dominio y la convierte a Markdown.

        Usa cabeceras de navegador para evitar bloqueos 403, BeautifulSoup para
        localizar el contenedor del dominio y markdownify para generar Markdown
        estructurado. Recurre a ``<body>`` si el selector configurado no se encuentra.

        Args:
            url: URL de la página a obtener.
            config: Configuración del dominio con el selector y las reglas de limpieza.

        Returns:
            ``RawPage`` con el contenido procesado, o ``None`` en caso de error de red.
        """
        import urllib3
        import requests as req_lib

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        normalized_url = _HTTP_URL_ADAPTER.validate_python(str(url))
        self.client.rate_limiter.wait()
        try:
            response = req_lib.get(
                str(normalized_url),
                headers=self._BROWSER_HEADERS,
                timeout=self.settings.request_timeout,
                verify=False,
            )
            response.raise_for_status()
        except Exception as exc:
            logger.warning(
                "[domain_crawler] Could not fetch %s: %s",
                normalized_url,
                exc,
            )
            return None

        soup = BeautifulSoup(response.content, "html.parser")

        for tag in soup.select(_DOMAIN_NOISE_SELECTOR):
            tag.decompose()

        container = soup.select_one(config.container_selector)
        if container is None:
            logger.warning(
                "[domain_crawler] Selector '%s' not found in %s — falling back to <body>",
                config.container_selector,
                normalized_url,
            )
            container = soup.body or soup

        markdown_content = md(
            str(container), heading_style="ATX", strip=["script", "style"]
        )
        markdown_content = re.sub(
            r"\[(Agenda una cita|Agenda tu cita|Ver especialidad|Ver todos los servicios y especialidades|Agendar cita médica|Agendar chequeo médico|Encontrar un especialista|Prepararme para exámenes médicos|Especialidades|Realizar pagos|Ver resultados médicos|Solicitar cita por Whatsapp|Solicitar una llamada|Directorio médico|Contáctenos|Conoce más|¿Cómo llegar\?|Preparación para exámenes y procedimientos|Hospital Padrino|Biblioteca|FVL al día|Buscar especialidad|Especialistas)\]\([^)]+\)",
            "",
            markdown_content,
            flags=re.IGNORECASE,
        )
        markdown_content = re.sub(
            r"\[Ver especialidad\]\([^)]+\)", "", markdown_content
        )
        markdown_content = re.sub(
            r"\[Ver todos los servicios y especialidades\]\([^)]+\)",
            "",
            markdown_content,
        )
        markdown_content = re.sub(
            r"(?:---\n\n)?## Otros especialistas.*",
            "",
            markdown_content,
            flags=re.DOTALL | re.IGNORECASE,
        )
        markdown_content = re.sub(
            r"\[([^\]\n]+)\]\(https?://[^\)\n]+/buscador-integral/[^\)\n]*\)",
            r"\1",
            markdown_content,
        )
        markdown_content = _clean_domain_markdown(markdown_content, config)

        extra: dict[str, str] = {}
        for field_name, selector in config.extra_metadata_selectors.items():
            el = soup.select_one(selector)
            if el:
                extra[field_name] = el.get_text(separator=" ", strip=True)

        h1 = soup.find("h1")
        title_tag = soup.find("title")
        raw_title = h1 or title_tag
        title = (
            raw_title.get_text(strip=True)[:200] if raw_title else str(normalized_url)
        )

        return RawPage(
            url=normalized_url,
            title=title,
            html=response.text,
            text_content=markdown_content,
            markdown=markdown_content,
            extra_metadata=extra,
            metadata=ExtractionMetadata(
                source_url=_HTTP_URL_ADAPTER.validate_python(str(response.url)),
                source_name=self.source_name,
                extractor_name="domain_web_crawler",
                http_status=response.status_code,
                content_type=response.headers.get("content-type"),
            ),
        )

    def fetch(self, url: str | AnyHttpUrl) -> RawPage:
        """Obtiene una página pública y la convierte al esquema ``RawPage``.

        Verifica el ``robots.txt`` antes de realizar la petición si está habilitado.

        Args:
            url: URL absoluta de la página a obtener.

        Returns:
            ``RawPage`` con el contenido y los metadatos de la extracción.

        Raises:
            CrawlBlockedError: Si la URL está bloqueada por el ``robots.txt``.
            httpx.HTTPStatusError: Si el servidor responde con un código de error HTTP.
        """
        if self.settings.respect_robots_txt:
            decision = self.robots_policy.evaluate(str(url))
            if not decision.allowed:
                raise CrawlBlockedError(
                    f"URL blocked by robots policy: {url} ({decision.reason})"
                )

        response = self.client.get(str(url))
        response.raise_for_status()
        html = decode_html(response)
        meta_description = extract_meta_description(html)
        text_content, has_primary = extract_text_content(html)
        if meta_description and not has_primary:
            text_content = f"{meta_description}\n\n{text_content}".strip()

        source_url = _HTTP_URL_ADAPTER.validate_python(str(response.url))
        metadata = ExtractionMetadata(
            source_url=source_url,
            source_name=self.source_name,
            extractor_name="web_crawler",
            http_status=response.status_code,
            content_type=response.headers.get("content-type"),
        )
        return RawPage(
            url=source_url,
            title=extract_title(html),
            html=html,
            text_content=text_content,
            metadata=metadata,
        )
