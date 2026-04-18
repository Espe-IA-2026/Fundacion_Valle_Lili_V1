from __future__ import annotations

import sys
from datetime import UTC, datetime

from semantic_layer_fvl import cli
from semantic_layer_fvl.schemas import PipelineItemResult, PipelineRunSummary


def build_summary(*, success: bool = True) -> PipelineRunSummary:
    result = PipelineItemResult(
        source_type="web",
        input_reference="https://valledellili.org/quienes-somos",
        success=success,
        title="Quienes Somos" if success else None,
        category="01_organizacion" if success else None,
        slug="quienes-somos" if success else None,
        error=None if success else "network failure",
    )
    return PipelineRunSummary(
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        write_enabled=False,
        results=[result],
    )


def test_print_summary_renders_counts_and_items(capsys) -> None:
    cli.print_summary(build_summary(), summary_path="D:/runs/run-summary.json")

    captured = capsys.readouterr().out

    assert "processed=1" in captured
    assert "success=1" in captured
    assert 'summary_path="D:/runs/run-summary.json"' in captured
    assert 'ok source="web"' in captured


def test_main_dispatches_crawl_seeds(monkeypatch, capsys) -> None:
    class StubPipeline:
        def run_seed_urls(self, *, limit: int | None = None, write: bool = False) -> PipelineRunSummary:
            assert limit == 2
            assert write is False
            return build_summary()

        def save_summary(self, summary: PipelineRunSummary) -> str:
            return "D:/runs/summary.json"

    monkeypatch.setattr(cli, "SemanticPipeline", StubPipeline)
    monkeypatch.setattr(cli, "configure_logging", lambda: None)
    monkeypatch.setattr(sys, "argv", ["semantic-layer-fvl", "crawl-seeds", "--limit", "2"])

    exit_code = cli.main()
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert "processed=1" in captured


def test_main_dispatches_run_all_and_returns_failure_code(monkeypatch, capsys) -> None:
    class StubPipeline:
        def run_all(
            self,
            *,
            seed_limit: int | None = None,
            youtube_feed_urls: list[str] | None = None,
            news_feed_urls: list[str] | None = None,
            write: bool = False,
        ) -> PipelineRunSummary:
            assert seed_limit == 3
            assert youtube_feed_urls == ["https://youtube.test/feed"]
            assert news_feed_urls == ["https://news.test/feed.xml"]
            assert write is False
            return build_summary(success=False)

        def save_summary(self, summary: PipelineRunSummary) -> str:
            return "D:/runs/summary.json"

    monkeypatch.setattr(cli, "SemanticPipeline", StubPipeline)
    monkeypatch.setattr(cli, "configure_logging", lambda: None)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "semantic-layer-fvl",
            "run-all",
            "--seed-limit",
            "3",
            "--youtube-feed",
            "https://youtube.test/feed",
            "--news-feed",
            "https://news.test/feed.xml",
        ],
    )

    exit_code = cli.main()
    captured = capsys.readouterr().out

    assert exit_code == 1
    assert "failure=1" in captured
    assert 'error="network failure"' in captured
