from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import AnyHttpUrl, BaseModel, Field


class DocumentCategory(StrEnum):
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
    DRAFT = "draft"
    READY = "ready"
    PUBLISHED = "published"
    ERROR = "error"


class ExtractionMetadata(BaseModel):
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source_url: AnyHttpUrl
    source_name: str
    extractor_name: str
    http_status: int | None = Field(default=None, ge=100, le=599)
    content_type: str | None = None
    checksum: str | None = None


class UrlRecord(BaseModel):
    url: AnyHttpUrl
    category: DocumentCategory | None = None
    priority: int = Field(default=100, ge=1)
    discovered_from: AnyHttpUrl | None = None
    notes: str | None = None
    active: bool = True


class RawPage(BaseModel):
    url: AnyHttpUrl
    title: str | None = None
    html: str | None = None
    markdown: str | None = None
    text_content: str | None = None
    metadata: ExtractionMetadata
    extra_metadata: dict[str, str] = Field(default_factory=dict)


class SourceDocument(BaseModel):
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


class ProcessedDocument(BaseModel):
    document: SourceDocument
    content_markdown: str
    headings: list[str] = Field(default_factory=list)
    related_urls: list[AnyHttpUrl] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    extra_metadata: dict[str, str] = Field(default_factory=dict)


