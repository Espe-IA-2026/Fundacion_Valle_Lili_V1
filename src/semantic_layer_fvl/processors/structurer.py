"""Conversión de páginas crudas en documentos semánticos estructurados."""

from __future__ import annotations

import re
import unicodedata
from urllib.parse import parse_qs, urlsplit

from semantic_layer_fvl.schemas import (
    DocumentCategory,
    ProcessedDocument,
    PublicationStatus,
    RawPage,
    SourceDocument,
)

PATH_CATEGORY_RULES: tuple[tuple[str, DocumentCategory], ...] = (
    # More-specific paths before their parent prefixes
    ("/nuestra-institucion/nuestras-sedes", DocumentCategory.SEDES_UBICACIONES),
    ("/nuestra-institucion/marco-legal", DocumentCategory.NORMATIVIDAD),
    (
        "/nuestra-institucion/politica-de-tratamiento-de-datos",
        DocumentCategory.NORMATIVIDAD,
    ),
    ("/nuestra-institucion", DocumentCategory.ORGANIZACION),
    ("/quienes-somos", DocumentCategory.ORGANIZACION),
    ("/atencion-al-paciente/educacion-al-paciente", DocumentCategory.EDUCACION),
    ("/atencion-al-paciente", DocumentCategory.SERVICIOS),
    ("/servicios", DocumentCategory.SERVICIOS),
    ("/especialidades", DocumentCategory.SERVICIOS),
    ("/directorio-medico", DocumentCategory.TALENTO_HUMANO),
    ("/sedes", DocumentCategory.SEDES_UBICACIONES),
    ("/contacto", DocumentCategory.CONTACTO),
    ("/contactanos", DocumentCategory.CONTACTO),
    ("/normatividad", DocumentCategory.NORMATIVIDAD),
    ("/comite-de-etica-en-investigacion-biomedica", DocumentCategory.INVESTIGACION),
    ("/investigacion", DocumentCategory.INVESTIGACION),
    ("/educacion", DocumentCategory.EDUCACION),
    ("/noticias-y-eventos", DocumentCategory.NOTICIAS),
    ("/noticias", DocumentCategory.NOTICIAS),
    ("/publicaciones", DocumentCategory.NOTICIAS),
    ("/blog", DocumentCategory.NOTICIAS),
    ("/videos", DocumentCategory.MULTIMEDIA),
)

KEYWORD_CATEGORY_RULES: tuple[tuple[tuple[str, ...], DocumentCategory], ...] = (
    (("mision", "vision", "historia"), DocumentCategory.ORGANIZACION),
    (("servicio", "especialidad", "consulta"), DocumentCategory.SERVICIOS),
    (
        ("doctor", "medico", "especialista", "directorio"),
        DocumentCategory.TALENTO_HUMANO,
    ),
    (("sede", "ubicacion", "direccion"), DocumentCategory.SEDES_UBICACIONES),
    (("contacto", "telefono", "correo"), DocumentCategory.CONTACTO),
    (("politica", "derechos", "normatividad"), DocumentCategory.NORMATIVIDAD),
    (("investigacion", "ensayo", "cientifico"), DocumentCategory.INVESTIGACION),
    (("educacion", "curso", "formacion"), DocumentCategory.EDUCACION),
    (("noticia", "boletin", "actualidad"), DocumentCategory.NOTICIAS),
    (("video", "youtube", "multimedia"), DocumentCategory.MULTIMEDIA),
)

_RE_MD_LINK = re.compile(r'\[([^\]\n]+)\]\([^\)\n]+\)')
_RE_REAL_WORD = re.compile(r'[a-zA-ZáéíóúñüÁÉÍÓÚÑÜ]{4,}')
_RE_NOISE_START = re.compile(r'^(?:https?://|!\[|/[\w./%-]{5,})')


def slugify(value: str) -> str:
    """Convierte una cadena en un slug URL-safe en minúsculas sin acentos.

    Args:
        value: Texto a convertir (título, ruta u otro identificador).

    Returns:
        Slug normalizado, o ``"documento"`` si el resultado queda vacío.
    """
    normalized = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    )
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", normalized).strip("-").lower()
    return normalized or "documento"


class SemanticStructurer:
    """Convierte páginas crudas limpias en documentos semánticos procesados."""

    def infer_category(self, raw_page: RawPage, cleaned_text: str) -> DocumentCategory:
        """Infiere la categoría del documento a partir de la URL y el texto limpio.

        Aplica primero las reglas por prefijo de ruta (``PATH_CATEGORY_RULES``) y,
        si no hay coincidencia, las reglas por palabras clave (``KEYWORD_CATEGORY_RULES``).
        Devuelve ``ORGANIZACION`` como categoría por defecto.

        Args:
            raw_page: Página cruda con la URL de origen.
            cleaned_text: Texto limpio del contenido de la página.

        Returns:
            ``DocumentCategory`` inferida para el documento.
        """
        path = urlsplit(str(raw_page.url)).path.lower()
        for prefix, category in PATH_CATEGORY_RULES:
            if path == prefix or path.startswith(f"{prefix}/"):
                return category

        path_segments = [segment for segment in path.split("/") if segment]
        for segment in path_segments:
            normalized_segment = f"/{segment}"
            for prefix, category in PATH_CATEGORY_RULES:
                if normalized_segment == prefix:
                    return category

        if path in {"", "/"}:
            return DocumentCategory.ORGANIZACION

        # Include URL path so slugs like /investigacion-* match keyword rules
        combined_text = " ".join(
            filter(None, [raw_page.title, cleaned_text, path])
        ).casefold()
        for keywords, category in KEYWORD_CATEGORY_RULES:
            if any(keyword in combined_text for keyword in keywords):
                return category

        return DocumentCategory.ORGANIZACION

    def build_document(
        self,
        raw_page: RawPage,
        cleaned_text: str,
        *,
        category: DocumentCategory | None = None,
        domain_name: str | None = None,
    ) -> ProcessedDocument:
        """Construye un ``ProcessedDocument`` a partir de una página cruda y su texto limpio.

        Si se indica ``domain_name``, usa el Markdown ya generado en ``raw_page.markdown``
        y la categoría definida en la configuración del dominio; de lo contrario, infiere
        la categoría y construye el cuerpo Markdown desde ``cleaned_text``.

        Args:
            raw_page: Página cruda con URL, título y metadatos de extracción.
            cleaned_text: Texto limpio del contenido de la página.
            category: Categoría a asignar manualmente (ignorada si se indica ``domain_name``).
            domain_name: Nombre del dominio configurado (p.ej. ``"servicios"``).

        Returns:
            ``ProcessedDocument`` listo para ser escrito como archivo Markdown.
        """
        if domain_name is not None:
            from semantic_layer_fvl.domains import DOMAIN_CONFIGS

            domain_cfg = DOMAIN_CONFIGS[domain_name]
            resolved_category = DocumentCategory(domain_cfg.category)
        else:
            resolved_category = category or self.infer_category(raw_page, cleaned_text)

        title = self._resolve_title(raw_page)
        slug = self._resolve_slug(raw_page, title)

        if domain_name is not None and raw_page.markdown:
            markdown_body = raw_page.markdown
            summary = self._build_summary(raw_page.markdown)
        else:
            summary = self._build_summary(cleaned_text)
            markdown_body = self._build_markdown_body(title, cleaned_text)

        source_document = SourceDocument(
            document_id=f"{resolved_category.value}-{slug}",
            title=title,
            slug=slug,
            category=resolved_category,
            source_url=raw_page.url,
            source_name=raw_page.metadata.source_name,
            summary=summary,
            status=(
                PublicationStatus.READY
                if markdown_body.strip()
                else PublicationStatus.DRAFT
            ),
            extraction_metadata=raw_page.metadata,
        )
        return ProcessedDocument(
            document=source_document,
            content_markdown=markdown_body,
            headings=self._extract_headings(markdown_body),
            extra_metadata=dict(raw_page.extra_metadata),
        )

    @staticmethod
    def _resolve_title(raw_page: RawPage) -> str:
        """Devuelve el título de la página, derivándolo de la URL si no está disponible."""
        if raw_page.title and raw_page.title.strip():
            return raw_page.title.strip()

        path = urlsplit(str(raw_page.url)).path.strip("/")
        if not path:
            return "Inicio"
        return path.rsplit("/", 1)[-1].replace("-", " ").title()

    @staticmethod
    def _resolve_slug(raw_page: RawPage, title: str) -> str:
        """Genera el slug del documento priorizando identificadores externos.

        Orden de prioridad:
            1. ``extra_metadata.video_id`` o ``external_id`` (e.g., YouTube, GUID feed).
            2. Para URLs de YouTube, el query param ``v=...``.
            3. Último segmento del path de la URL (excluye genéricos como ``watch``).
            4. Slug derivado del título.
        """
        # 1) Identificador externo en extra_metadata
        for key in ("video_id", "external_id"):
            ext_id = raw_page.extra_metadata.get(key) if raw_page.extra_metadata else None
            if ext_id:
                return slugify(str(ext_id))

        parts = urlsplit(str(raw_page.url))

        # 2) Query param `v` en URLs de YouTube
        if "youtube.com" in parts.netloc or "youtu.be" in parts.netloc:
            video_param = parse_qs(parts.query).get("v", [None])[0]
            if video_param:
                return slugify(video_param)

        # 3) Último segmento del path (excluyendo genéricos)
        _GENERIC_SEGMENTS = {"watch", "rss", "feed", "index", "articles"}
        path = parts.path.strip("/")
        if path:
            last_segment = path.rsplit("/", 1)[-1]
            slug_candidate = slugify(last_segment)
            if slug_candidate and slug_candidate not in _GENERIC_SEGMENTS:
                return slug_candidate

        # 4) Fallback al título
        return slugify(title)

    @staticmethod
    def _build_summary(cleaned_text: str, max_length: int = 220) -> str | None:
        """Extrae el primer párrafo significativo del texto limpio como resumen del documento.

        Args:
            cleaned_text: Texto limpio con párrafos separados por líneas en blanco.
            max_length: Longitud máxima del resumen en caracteres (por defecto 220).

        Returns:
            Cadena resumen truncada si es necesario, o ``None`` si no hay párrafo válido.
        """
        stripped = cleaned_text.strip()
        if not stripped:
            return None
        for paragraph in stripped.split("\n\n"):
            candidate = _RE_MD_LINK.sub(r'\1', paragraph.replace("\n", " ").strip())
            if not candidate or _RE_NOISE_START.match(candidate):
                continue
            if len(_RE_REAL_WORD.findall(candidate)) < 4:
                continue
            if len(candidate) <= max_length:
                return candidate
            truncated = candidate[:max_length].rsplit(" ", 1)[0].rstrip(".,;: ")
            return f"{truncated}..."
        return None

    @staticmethod
    def _build_markdown_body(title: str, cleaned_text: str) -> str:
        """Construye el cuerpo Markdown del documento con el título como H1 y los párrafos del texto."""
        paragraphs = [
            chunk.strip() for chunk in cleaned_text.split("\n\n") if chunk.strip()
        ]
        lines = [f"# {title}", ""]

        if not paragraphs:
            lines.append("_Contenido pendiente de estructurar._")
            return "\n".join(lines).strip()

        for paragraph in paragraphs:
            lines.append(paragraph)
            lines.append("")

        return "\n".join(lines).strip()

    @staticmethod
    def _extract_headings(markdown_body: str) -> list[str]:
        """Extrae la lista de encabezados Markdown (sin prefijos ``#``) del cuerpo del documento."""
        headings: list[str] = []
        for line in markdown_body.splitlines():
            if line.startswith("#"):
                headings.append(line.lstrip("# ").strip())
        return headings
