"""Configuración centralizada del proyecto cargada desde variables de entorno."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AnyHttpUrl, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración central del proyecto cargada desde variables de entorno.

    Los valores se leen del archivo ``.env`` y pueden sobreescribirse con
    variables de entorno del sistema operativo (sin distinción de mayúsculas).
    """

    project_name: str = "semantic-layer-fvl"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # Rutas principales
    knowledge_dir: Path = Path("./data/knowledge")
    chroma_persist_dir: Path = Path("./data/chroma_db")
    runs_dir: Path = Path("./reports/runs")
    structured_data_path: Path = Path("data/structured/fvl_info.json")

    # Módulo 2 — RAG
    embedding_model: str = "text-embedding-3-small"
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-5-nano"
    rag_top_k: int = Field(default=5, ge=1)
    rag_score_threshold: float = Field(default=0.3, ge=0.0, le=1.0)
    agent_max_iterations: int = Field(default=6, ge=1)

    # HTTP
    requests_per_second: float = Field(default=0.5, gt=0)
    request_timeout: int = Field(default=30, gt=0)
    max_retries: int = Field(default=2, ge=0)
    user_agent: str = "semantic-layer-fvl/0.1.0"
    accept_language: str = "es-CO,es;q=0.9,en;q=0.8"

    target_base_url: AnyHttpUrl = Field(default=AnyHttpUrl("https://valledellili.org"))
    respect_robots_txt: bool = True

    # YouTube y noticias
    youtube_search_limit: int = Field(default=50, ge=1)
    news_feed_limit: int = Field(default=50, ge=1)
    news_search_days: int = Field(default=365, ge=1)
    youtube_search_queries: list[str] = Field(
        default=["Fundación Valle del Lili", "Hospital Valle del Lili"],
    )
    youtube_transcript_languages: list[str] = Field(
        default=["es", "es-419", "es-CO", "en"],
    )
    news_curated_enabled: bool = True
    news_google_queries: list[str] = Field(
        default=["Fundación Valle del Lili", "FVL Cali"],
    )
    news_fetch_full_article: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def request_interval_seconds(self) -> float:
        """Intervalo mínimo en segundos entre peticiones HTTP consecutivas."""
        return 1 / self.requests_per_second

    @property
    def project_root(self) -> Path:
        """Ruta absoluta a la raíz del proyecto (tres niveles sobre este archivo)."""
        return Path(__file__).resolve().parents[3]

    @property
    def resolved_knowledge_dir(self) -> Path:
        """Ruta absoluta al directorio de conocimiento, resuelta desde la raíz del proyecto."""
        if self.knowledge_dir.is_absolute():
            return self.knowledge_dir
        return (self.project_root / self.knowledge_dir).resolve()

    @property
    def resolved_chroma_persist_dir(self) -> Path:
        """Ruta absoluta al directorio de persistencia de ChromaDB."""
        if self.chroma_persist_dir.is_absolute():
            return self.chroma_persist_dir
        return (self.project_root / self.chroma_persist_dir).resolve()

    @property
    def resolved_runs_dir(self) -> Path:
        """Ruta absoluta al directorio de reportes de corridas."""
        if self.runs_dir.is_absolute():
            return self.runs_dir
        return (self.project_root / self.runs_dir).resolve()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Devuelve la instancia singleton de ``Settings`` (resultado en caché)."""
    return Settings()
