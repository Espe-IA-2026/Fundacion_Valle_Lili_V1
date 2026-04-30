"""Modelos Pydantic que representan los documentos en la capa semántica.

Incluye enumeraciones de categoría y estado, así como los modelos de datos
``ExtractionMetadata``, ``UrlRecord``, ``RawPage``, ``SourceDocument`` y
``ProcessedDocument``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, Field
from enum import StrEnum


class DocumentCategory(StrEnum):
    """Categorías temáticas que clasifican los documentos extraídos del sitio.

    El prefijo numérico ordena las categorías de forma consistente en el
    sistema de archivos y en los reportes de corrida.
    """

    ORGANIZACION = "01_organizacion"
    SERVICIOS = "02_servicios"
    TALENTO_HUMANO = "03_talento_humano"
    SEDES_UBICACIONES = "04_sedes_ubicaciones"
    CONTACTO = "05_contacto"
    NORMATIVIDAD = "06_normatividad"
    INVESTIGACION = "07_investigacion"
    EDUCACION = "08_educacion"
    NOTICIAS = "09_noticias"
    MULTIMEDIA = "10_multimedia"


class PublicationStatus(StrEnum):
    """Estado de publicación de un documento en el pipeline de extracción."""

    DRAFT = "draft"
    READY = "ready"
    PUBLISHED = "published"
    ERROR = "error"


class ExtractionMetadata(BaseModel):
    """Metadatos técnicos registrados durante la extracción de un recurso web.

    Attributes:
        extracted_at: Marca de tiempo UTC en que se realizó la extracción.
        source_url: URL final del recurso (tras posibles redirecciones).
        source_name: Nombre legible de la fuente (p.ej. ``"Fundacion Valle del Lili"``).
        extractor_name: Identificador del extractor utilizado.
        http_status: Código de respuesta HTTP recibido (100-599).
        content_type: Valor de la cabecera ``Content-Type`` de la respuesta.
        checksum: Hash opcional del contenido para detección de cambios.
    """

    extracted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source_url: AnyHttpUrl
    source_name: str
    extractor_name: str
    http_status: int | None = Field(default=None, ge=100, le=599)
    content_type: str | None = None
    checksum: str | None = None


class UrlRecord(BaseModel):
    """Registro de una URL descubierta o semilla, con metadatos de categoría y prioridad.

    Attributes:
        url: URL absoluta del recurso.
        category: Categoría temática inferida o asignada manualmente.
        priority: Valor numérico de prioridad (menor = mayor importancia).
        discovered_from: URL desde la cual se descubrió este registro.
        notes: Notas opcionales sobre el origen o propósito de la URL.
        active: Indica si la URL debe incluirse en las corridas del pipeline.
    """

    url: AnyHttpUrl
    category: DocumentCategory | None = None
    priority: int = Field(default=100, ge=1)
    discovered_from: AnyHttpUrl | None = None
    notes: str | None = None
    active: bool = True


class RawPage(BaseModel):
    """Contenido crudo de una página web tal como fue extraído por un extractor.

    Attributes:
        url: URL del recurso extraído.
        title: Título de la página (etiqueta ``<title>`` u ``og:title``).
        html: HTML original de la respuesta, si fue obtenido.
        markdown: Versión Markdown del contenido, si fue generada por el extractor.
        text_content: Texto plano del contenido principal de la página.
        metadata: Metadatos técnicos de la extracción.
        extra_metadata: Campos adicionales capturados mediante selectores CSS personalizados.
    """

    url: AnyHttpUrl
    title: str | None = None
    html: str | None = None
    markdown: str | None = None
    text_content: str | None = None
    metadata: ExtractionMetadata
    extra_metadata: dict[str, str] = Field(default_factory=dict)


class SourceDocument(BaseModel):
    """Documento estructurado con metadatos semánticos, previo al enriquecimiento final.

    Attributes:
        document_id: Identificador único con formato ``{categoria}-{slug}``.
        title: Título normalizado del documento.
        slug: Versión URL-friendly del título o la ruta de la página.
        category: Categoría temática del documento.
        source_url: URL original del recurso.
        source_name: Nombre de la fuente (institución o canal).
        tags: Etiquetas opcionales para búsqueda y filtrado.
        summary: Resumen automático del contenido (máx. 220 caracteres).
        status: Estado de publicación del documento.
        extraction_metadata: Metadatos técnicos de la extracción.
    """

    document_id: str
    title: str
    slug: str
    category: DocumentCategory
    source_url: AnyHttpUrl
    source_name: str
    tags: list[str] = Field(default_factory=list)
    summary: str | None = None
    status: PublicationStatus = PublicationStatus.DRAFT
    extraction_metadata: ExtractionMetadata
    source_type: Literal[
        "web_fvl", "youtube_rich", "youtube_feed", "news_curated", "news_google", "news_feed"
    ] | None = None
    external_id: str | None = None
    published_at: datetime | None = None


class ProcessedDocument(BaseModel):
    """Documento completamente procesado listo para ser escrito como archivo Markdown.

    Attributes:
        document: Metadatos semánticos del documento fuente.
        content_markdown: Cuerpo del documento en formato Markdown.
        headings: Lista de encabezados extraídos del Markdown (sin prefijos ``#``).
        related_urls: URLs relacionadas encontradas durante la extracción.
        warnings: Advertencias generadas durante el procesamiento.
        extra_metadata: Metadatos adicionales capturados por selectores CSS.
    """

    document: SourceDocument
    content_markdown: str
    headings: list[str] = Field(default_factory=list)
    related_urls: list[AnyHttpUrl] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    extra_metadata: dict[str, str] = Field(default_factory=dict)


