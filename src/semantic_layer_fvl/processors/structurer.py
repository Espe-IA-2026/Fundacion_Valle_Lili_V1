from __future__ import annotations

import re
import unicodedata
from urllib.parse import urlsplit

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
    ("/nuestra-institucion/politica-de-tratamiento-de-datos", DocumentCategory.NORMATIVIDAD),
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
    (("doctor", "medico", "especialista", "directorio"), DocumentCategory.TALENTO_HUMANO),
    (("sede", "ubicacion", "direccion"), DocumentCategory.SEDES_UBICACIONES),
    (("contacto", "telefono", "correo"), DocumentCategory.CONTACTO),
    (("politica", "derechos", "normatividad"), DocumentCategory.NORMATIVIDAD),
    (("investigacion", "ensayo", "cientifico"), DocumentCategory.INVESTIGACION),
    (("educacion", "curso", "formacion"), DocumentCategory.EDUCACION),
    (("noticia", "boletin", "actualidad"), DocumentCategory.NOTICIAS),
    (("video", "youtube", "multimedia"), DocumentCategory.MULTIMEDIA),
)


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", normalized).strip("-").lower()
    return normalized or "documento"


class SemanticStructurer:
    """Converts cleaned raw pages into processed semantic documents."""

    def infer_category(self, raw_page: RawPage, cleaned_text: str) -> DocumentCategory:
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
        combined_text = " ".join(filter(None, [raw_page.title, cleaned_text, path])).casefold()
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
            source_url=str(raw_page.url),
            source_name=raw_page.metadata.source_name,
            summary=summary,
            status=PublicationStatus.READY if markdown_body.strip() else PublicationStatus.DRAFT,
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
        if raw_page.title and raw_page.title.strip():
            return raw_page.title.strip()

        path = urlsplit(str(raw_page.url)).path.strip("/")
        if not path:
            return "Inicio"
        return path.rsplit("/", 1)[-1].replace("-", " ").title()

    @staticmethod
    def _resolve_slug(raw_page: RawPage, title: str) -> str:
        path = urlsplit(str(raw_page.url)).path.strip("/")
        if path:
            return slugify(path.rsplit("/", 1)[-1])
        return slugify(title)

    @staticmethod
    def _build_summary(cleaned_text: str, max_length: int = 220) -> str | None:
        stripped = cleaned_text.strip()
        if not stripped:
            return None

        summary = stripped.split("\n\n", 1)[0].replace("\n", " ")
        if len(summary) <= max_length:
            return summary
        truncated = summary[:max_length].rsplit(" ", 1)[0].rstrip(".,;: ")
        return f"{truncated}..."

    @staticmethod
    def _build_markdown_body(title: str, cleaned_text: str) -> str:
        paragraphs = [chunk.strip() for chunk in cleaned_text.split("\n\n") if chunk.strip()]
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
        headings: list[str] = []
        for line in markdown_body.splitlines():
            if line.startswith("#"):
                headings.append(line.lstrip("# ").strip())
        return headings
