from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


class PipelineItemResult(BaseModel):
    source_type: Literal["web", "youtube_feed", "news_feed", "web_discovered"]
    input_reference: str
    success: bool
    title: str | None = None
    category: str | None = None
    slug: str | None = None
    output_path: str | None = None
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None


class PipelineRunSummary(BaseModel):
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None
    write_enabled: bool = False
    results: list[PipelineItemResult] = Field(default_factory=list)

    @property
    def processed_count(self) -> int:
        return len(self.results)

    @property
    def success_count(self) -> int:
        return sum(1 for result in self.results if result.success)

    @property
    def failure_count(self) -> int:
        return sum(1 for result in self.results if not result.success)
