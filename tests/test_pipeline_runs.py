from __future__ import annotations

from pathlib import Path

from semantic_layer_fvl.config.settings import Settings
from semantic_layer_fvl.orchestrator import SemanticPipeline
from semantic_layer_fvl.schemas import ExtractionMetadata, RawPage


class StubCrawler:
    def fetch(self, url: str) -> RawPage:
        if "error" in url:
            raise RuntimeError("network failure")
        return RawPage(
            url=url,
            title="Pagina institucional",
            text_content="Informacion institucional.\n\nDetalle de servicio.",
            metadata=ExtractionMetadata(
                source_url=url,
                source_name="Fundacion Valle del Lili",
                extractor_name="stub_crawler",
            ),
        )


class DiscoveryCrawler:
    """Stub that returns HTML with discoverable links for the home seed URL."""

    _PAGES: dict[str, str] = {
        "https://valledellili.org": (
            "<html><body>"
            '<a href="/descubierta">Descubierta</a>'
            "</body></html>"
        ),
        "https://valledellili.org/descubierta": (
            "<html><head><title>Pagina descubierta</title></head>"
            "<body><main><p>Contenido de la pagina descubierta.</p></main></body></html>"
        ),
    }

    def fetch(self, url: str) -> RawPage:
        normalized = url.rstrip("/")
        html = self._PAGES.get(normalized, "<html><body><p>Pagina generica.</p></body></html>")
        return RawPage(
            url=url,
            title="Titulo stub",
            html=html,
            text_content="Contenido stub.",
            metadata=ExtractionMetadata(
                source_url=url,
                source_name="Fundacion Valle del Lili",
                extractor_name="stub_crawler",
            ),
        )


def test_run_urls_collects_success_and_failure_results() -> None:
    pipeline = SemanticPipeline(settings=Settings(), crawler=StubCrawler())

    summary = pipeline.run_urls(
        [
            "https://valledellili.org/quienes-somos",
            "https://valledellili.org/error",
        ]
    )

    assert summary.processed_count == 2
    assert summary.success_count == 1
    assert summary.failure_count == 1
    assert summary.finished_at is not None


def test_run_with_discovery_follows_links_from_seed() -> None:
    pipeline = SemanticPipeline(settings=Settings(), crawler=DiscoveryCrawler())
    summary = pipeline.run_with_discovery(max_pages=20)

    processed_urls = {r.input_reference.rstrip("/") for r in summary.results if r.success}
    assert "https://valledellili.org/descubierta" in processed_urls


def test_run_with_discovery_respects_max_pages() -> None:
    pipeline = SemanticPipeline(settings=Settings(), crawler=DiscoveryCrawler())
    summary = pipeline.run_with_discovery(max_pages=3)

    assert summary.processed_count <= 3


def test_save_summary_writes_json_report(workspace_tmp_path: Path) -> None:
    settings = Settings(runs_dir=workspace_tmp_path)
    pipeline = SemanticPipeline(settings=settings, crawler=StubCrawler())
    summary = pipeline.run_urls(["https://valledellili.org/quienes-somos"])
    captured: dict[str, str] = {}

    original_write_text = Path.write_text

    def fake_write_text(
        self: Path,
        data: str,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> int:
        captured["path"] = str(self)
        captured["data"] = data
        return len(data)

    Path.write_text = fake_write_text
    try:
        output_path = pipeline.save_summary(summary)
    finally:
        Path.write_text = original_write_text

    assert output_path.parent == workspace_tmp_path
    assert output_path.suffix == ".json"
    assert "processed_count" not in captured["data"]
    assert '"success": true' in captured["data"]
