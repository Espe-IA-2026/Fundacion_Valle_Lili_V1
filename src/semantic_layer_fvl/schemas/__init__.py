"""Submódulo de esquemas: expone todos los modelos Pydantic del dominio."""

from semantic_layer_fvl.schemas.documents import (
    DocumentCategory,
    ExtractionMetadata,
    ProcessedDocument,
    PublicationStatus,
    RawPage,
    SourceDocument,
    UrlRecord,
)
from semantic_layer_fvl.schemas.runs import PipelineItemResult, PipelineRunSummary

__all__ = [
    "DocumentCategory",
    "ExtractionMetadata",
    "PipelineItemResult",
    "PipelineRunSummary",
    "ProcessedDocument",
    "PublicationStatus",
    "RawPage",
    "SourceDocument",
    "UrlRecord",
]
