"""Extractor de feeds RSS y Atom de noticias hacia registros ``RawPage``."""

from __future__ import annotations

import email.utils
import re
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup
from pydantic import AnyHttpUrl, TypeAdapter

from semantic_layer_fvl.config import Settings, get_settings
from semantic_layer_fvl.extractors.http_client import HttpClient
from semantic_layer_fvl.schemas import ExtractionMetadata, RawPage


_HTTP_URL_ADAPTER = TypeAdapter(AnyHttpUrl)
_WHITESPACE_RE = re.compile(r"\s+")


def _strip_html(value: str | None) -> str | None:
    """Limpia HTML embebido (CDATA RSS) y normaliza el espacio en blanco."""
    if not value:
        return value
    if "<" in value and ">" in value:
        try:
            soup = BeautifulSoup(value, "html.parser")
            value = soup.get_text(separator=" ", strip=True)
        except Exception:
            pass
    cleaned = _WHITESPACE_RE.sub(" ", value).strip()
    return cleaned or None


class NewsFeedExtractor:
    """Parsea feeds RSS o Atom de noticias y los convierte en registros ``RawPage``."""

    def __init__(
        self,
        client: HttpClient | None = None,
        *,
        settings: Settings | None = None,
        source_name: str = "News Feed",
    ) -> None:
        """Inicializa el extractor de feeds de noticias.

        Args:
            client: Cliente HTTP a utilizar. Si es ``None`` se crea uno con ``settings``.
            settings: Configuración del proyecto. Si es ``None`` se obtiene la instancia global.
            source_name: Nombre de la fuente por defecto para los metadatos de extracción.
        """
        self.settings = settings or get_settings()
        self.client = client or HttpClient(self.settings)
        self.source_name = source_name

    def fetch_feed(self, feed_url: str) -> list[RawPage]:
        """Descarga el feed y lo parsea automáticamente como RSS o Atom.

        Args:
            feed_url: URL del feed RSS o Atom a procesar.

        Returns:
            Lista de ``RawPage`` con hasta ``news_feed_limit`` entradas.
        """
        response = self.client.get(feed_url)
        response.raise_for_status()

        root = ET.fromstring(response.text)
        if self._local_name(root.tag) == "rss":
            return self._parse_rss(
                response.text,
                response.status_code,
                response.headers.get("content-type"),
            )
        return self._parse_atom(
            root, response.status_code, response.headers.get("content-type")
        )

    def _parse_rss(
        self, xml_text: str, status_code: int, content_type: str | None
    ) -> list[RawPage]:
        """Parsea el XML de un feed RSS 2.0 y devuelve una lista de ``RawPage``."""
        root = ET.fromstring(xml_text)
        channel = root.find("channel")
        if channel is None:
            return []

        source_name = self._find_text(channel, "title") or self.source_name
        items = channel.findall("item")
        pages: list[RawPage] = []

        for item in items[: self.settings.news_feed_limit]:
            link = self._find_text(item, "link")
            title = _strip_html(self._find_text(item, "title"))
            if not link or not title:
                continue

            normalized_link = _HTTP_URL_ADAPTER.validate_python(link)

            description = _strip_html(self._find_text(item, "description"))
            content_encoded = _strip_html(
                self._find_text_with_namespace(
                    item, "content", "http://purl.org/rss/1.0/modules/content/"
                )
            )
            categories = self._find_categories(item)
            published = self._normalize_datetime(self._find_text(item, "pubDate"))
            metadata = ExtractionMetadata(
                source_url=normalized_link,
                source_name=source_name,
                extractor_name="news_feed",
                http_status=status_code,
                content_type=content_type,
            )
            body = content_encoded or description or ""
            cat_line = f"Categorías: {', '.join(categories)}" if categories else ""
            text_content = "\n\n".join(
                part for part in [title, body, cat_line, published] if part
            )
            pages.append(
                RawPage(
                    url=normalized_link,
                    title=title,
                    text_content=text_content,
                    metadata=metadata,
                )
            )

        return pages

    def _parse_atom(
        self, root: ET.Element, status_code: int, content_type: str | None
    ) -> list[RawPage]:
        """Parsea el árbol XML de un feed Atom y devuelve una lista de ``RawPage``."""
        source_name = self._find_text_ns(root, "title") or self.source_name
        pages: list[RawPage] = []
        entries = [child for child in root if self._local_name(child.tag) == "entry"]

        for entry in entries[: self.settings.news_feed_limit]:
            title = _strip_html(self._find_text_ns(entry, "title"))
            link = self._find_link_ns(entry)
            if not link or not title:
                continue

            normalized_link = _HTTP_URL_ADAPTER.validate_python(link)

            summary = _strip_html(
                self._find_text_ns(entry, "summary")
                or self._find_text_ns(entry, "content")
            )
            published = self._find_text_ns(entry, "updated") or self._find_text_ns(
                entry, "published"
            )
            metadata = ExtractionMetadata(
                source_url=normalized_link,
                source_name=source_name,
                extractor_name="news_feed",
                http_status=status_code,
                content_type=content_type,
            )
            text_content = "\n\n".join(
                part for part in [title, summary, published] if part
            )
            pages.append(
                RawPage(
                    url=normalized_link,
                    title=title,
                    text_content=text_content,
                    metadata=metadata,
                )
            )

        return pages

    @staticmethod
    def _find_text(element: ET.Element, tag: str) -> str | None:
        """Busca un hijo directo por nombre de etiqueta y devuelve su texto limpio."""
        found = element.find(tag)
        if found is None or found.text is None:
            return None
        text = found.text.strip()
        return text or None

    @staticmethod
    def _find_text_with_namespace(
        element: ET.Element, local_name: str, namespace: str
    ) -> str | None:
        """Busca un hijo con namespace (e.g. ``content:encoded``) y devuelve su texto."""
        qualified = f"{{{namespace}}}{local_name}"
        found = element.find(qualified)
        if found is None or found.text is None:
            return None
        text = found.text.strip()
        return text or None

    @staticmethod
    def _find_categories(element: ET.Element) -> list[str]:
        """Extrae todas las categorías declaradas en una entrada RSS."""
        categories: list[str] = []
        for child in element:
            if child.tag == "category" and child.text:
                category = child.text.strip()
                if category:
                    categories.append(category)
        return categories

    @classmethod
    def _find_text_ns(cls, element: ET.Element, local_name: str) -> str | None:
        """Busca un hijo por nombre local (ignorando namespace) y devuelve su texto."""
        for child in element:
            if cls._local_name(child.tag) == local_name and child.text:
                text = child.text.strip()
                if text:
                    return text
        return None

    @classmethod
    def _find_link_ns(cls, element: ET.Element) -> str | None:
        """Extrae la URL del primer elemento ``<link>`` de una entrada Atom."""
        for child in element:
            if cls._local_name(child.tag) != "link":
                continue
            href = child.attrib.get("href")
            if href:
                return href
            if child.text and child.text.strip():
                return child.text.strip()
        return None

    @staticmethod
    def _local_name(tag: str) -> str:
        """Extrae el nombre local de una etiqueta XML eliminando el prefijo de namespace."""
        return tag.rsplit("}", 1)[-1]

    @staticmethod
    def _normalize_datetime(value: str | None) -> str | None:
        """Normaliza una fecha en formato RFC 2822 a ISO 8601, o devuelve el valor original."""
        if not value:
            return None
        parsed = email.utils.parsedate_to_datetime(value)
        return parsed.isoformat() if parsed is not None else value
