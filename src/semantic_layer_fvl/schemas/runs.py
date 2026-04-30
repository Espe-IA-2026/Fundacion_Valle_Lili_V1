"""Modelos Pydantic que representan los resultados de una corrida del pipeline."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


class PipelineItemResult(BaseModel):
    """Resultado del procesamiento de un único ítem dentro de una corrida del pipeline.

    Attributes:
        source_type: Tipo de fuente procesada (``"web"``, ``"youtube_feed"``, etc.).
        input_reference: URL o identificador del recurso procesado.
        success: ``True`` si el ítem fue procesado sin errores.
        title: Título del documento generado (si fue exitoso).
        category: Valor de ``DocumentCategory`` asignado al documento.
        slug: Slug URL-friendly del documento.
        output_path: Ruta al archivo ``.md`` generado (si se escribió).
        warnings: Lista de advertencias no fatales del procesamiento.
        error: Mensaje de error si el procesamiento falló.
    """

    source_type: Literal[
        "web", "youtube_feed", "youtube_rich", "news_feed", "news_curated",
        "web_discovered", "web_domain",
    ]
    input_reference: str
    success: bool
    title: str | None = None
    category: str | None = None
    slug: str | None = None
    output_path: str | None = None
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None


class PipelineRunSummary(BaseModel):
    """Resumen agregado de una corrida completa del pipeline de extracción.

    Attributes:
        started_at: Marca de tiempo UTC de inicio de la corrida.
        finished_at: Marca de tiempo UTC de finalización (``None`` si aún está en curso).
        write_enabled: Indica si la corrida tenía habilitada la escritura de archivos.
        results: Lista de resultados individuales por ítem procesado.
    """

    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None
    write_enabled: bool = False
    results: list[PipelineItemResult] = Field(default_factory=list)

    @property
    def processed_count(self) -> int:
        """Número total de ítems procesados en la corrida."""
        return len(self.results)

    @property
    def success_count(self) -> int:
        """Número de ítems procesados exitosamente."""
        return sum(1 for result in self.results if result.success)

    @property
    def failure_count(self) -> int:
        """Número de ítems que fallaron durante el procesamiento."""
        return sum(1 for result in self.results if not result.success)
