from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central project settings loaded from environment variables."""

    project_name: str = "semantic-layer-fvl"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    output_dir: Path = Path("./knowledge")
    runs_dir: Path = Path("./runs")

    requests_per_second: float = Field(default=0.5, gt=0)
    request_timeout: int = Field(default=30, gt=0)
    max_retries: int = Field(default=2, ge=0)
    user_agent: str = "semantic-layer-fvl/0.1.0"
    accept_language: str = "es-CO,es;q=0.9,en;q=0.8"

    target_base_url: AnyHttpUrl = "https://valledellili.org"
    respect_robots_txt: bool = True

    youtube_search_limit: int = Field(default=50, ge=1)
    news_feed_limit: int = Field(default=50, ge=1)
    news_search_days: int = Field(default=365, ge=1)

    chroma_persist_dir: Path = Path("./vectorstore")
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    search_results_limit: int = Field(default=5, ge=1)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def request_interval_seconds(self) -> float:
        return 1 / self.requests_per_second

    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parents[3]

    @property
    def resolved_output_dir(self) -> Path:
        if self.output_dir.is_absolute():
            return self.output_dir
        return (self.project_root / self.output_dir).resolve()

    @property
    def resolved_runs_dir(self) -> Path:
        if self.runs_dir.is_absolute():
            return self.runs_dir
        return (self.project_root / self.runs_dir).resolve()

    @property
    def resolved_chroma_dir(self) -> Path:
        if self.chroma_persist_dir.is_absolute():
            return self.chroma_persist_dir
        return (self.project_root / self.chroma_persist_dir).resolve()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
