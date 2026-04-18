from __future__ import annotations

from semantic_layer_fvl.config.settings import Settings
from semantic_layer_fvl.orchestrator import SemanticPipeline
from semantic_layer_fvl.schemas import DocumentCategory, ExtractionMetadata, RawPage


class StubYouTubeExtractor:
    def fetch_feed(self, feed_url: str) -> list[RawPage]:
        return [
            RawPage(
                url="https://www.youtube.com/watch?v=xyz001",
                title="Video institucional",
                text_content="Video institucional\n\nDescripcion del video.",
                metadata=ExtractionMetadata(
                    source_url="https://www.youtube.com/watch?v=xyz001",
                    source_name="YouTube",
                    extractor_name="stub_youtube",
                ),
            )
        ]


class StubNewsExtractor:
    def fetch_feed(self, feed_url: str) -> list[RawPage]:
        return [
            RawPage(
                url="https://example.com/noticia-1",
                title="Nueva noticia",
                text_content="Nueva noticia\n\nResumen de la noticia.",
                metadata=ExtractionMetadata(
                    source_url="https://example.com/noticia-1",
                    source_name="Noticias",
                    extractor_name="stub_news",
                ),
            )
        ]


def test_pipeline_processes_youtube_feed_into_multimedia_documents() -> None:
    pipeline = SemanticPipeline(
        settings=Settings(),
        youtube_extractor=StubYouTubeExtractor(),
    )

    results = pipeline.process_youtube_feed("https://www.youtube.com/feeds/videos.xml?channel_id=test")

    assert len(results) == 1
    processed, output_path = results[0]
    assert output_path is None
    assert processed.document.category == DocumentCategory.MULTIMEDIA


def test_pipeline_processes_news_feed_into_news_documents() -> None:
    pipeline = SemanticPipeline(
        settings=Settings(),
        news_extractor=StubNewsExtractor(),
    )

    results = pipeline.process_news_feed("https://example.com/feed.xml")

    assert len(results) == 1
    processed, output_path = results[0]
    assert output_path is None
    assert processed.document.category == DocumentCategory.NOTICIAS
