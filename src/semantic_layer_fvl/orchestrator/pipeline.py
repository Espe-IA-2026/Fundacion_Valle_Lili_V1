from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from pathlib import Path

import yaml

from semantic_layer_fvl.config import Settings, get_settings
from semantic_layer_fvl.extractors.news import NewsFeedExtractor
from semantic_layer_fvl.extractors.site_map import build_seed_urls
from semantic_layer_fvl.extractors.web_crawler import CrawlBlockedError, WebCrawler, extract_links
from semantic_layer_fvl.extractors.youtube import YouTubeFeedExtractor
from semantic_layer_fvl.processors import SemanticStructurer, TextCleaner
from semantic_layer_fvl.schemas import (
    DocumentCategory,
    ExtractionMetadata,
    PipelineItemResult,
    PipelineRunSummary,
    ProcessedDocument,
    RawPage,
    SearchResult,
    SourceDocument,
)
from semantic_layer_fvl.writers import MarkdownWriter, VectorStoreWriter

logger = logging.getLogger(__name__)


class SemanticPipeline:
    """Minimal end-to-end pipeline from fetch to Markdown output."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        crawler: WebCrawler | None = None,
        youtube_extractor: YouTubeFeedExtractor | None = None,
        news_extractor: NewsFeedExtractor | None = None,
        cleaner: TextCleaner | None = None,
        structurer: SemanticStructurer | None = None,
        writer: MarkdownWriter | None = None,
        vectorstore_writer: VectorStoreWriter | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.crawler = crawler or WebCrawler(settings=self.settings)
        self.youtube_extractor = youtube_extractor or YouTubeFeedExtractor(settings=self.settings)
        self.news_extractor = news_extractor or NewsFeedExtractor(settings=self.settings)
        self.cleaner = cleaner or TextCleaner()
        self.structurer = structurer or SemanticStructurer()
        self.writer = writer or MarkdownWriter(self.settings)
        self.vectorstore_writer = vectorstore_writer

    def process_raw_page(
        self,
        raw_page: RawPage,
        *,
        category: DocumentCategory | None = None,
    ) -> ProcessedDocument:
        cleaned_text = self.cleaner.clean(raw_page.text_content)
        processed = self.structurer.build_document(raw_page, cleaned_text, category=category)
        if not cleaned_text:
            processed.warnings.append("empty_cleaned_text")
        return processed

    def _index_if_enabled(self, processed: ProcessedDocument) -> None:
        if self.vectorstore_writer is not None:
            self.vectorstore_writer.write(processed)

    def process_raw_pages(
        self,
        raw_pages: list[RawPage],
        *,
        category: DocumentCategory | None = None,
        write: bool = False,
    ) -> list[tuple[ProcessedDocument, Path | None]]:
        results: list[tuple[ProcessedDocument, Path | None]] = []
        for raw_page in raw_pages:
            processed = self.process_raw_page(raw_page, category=category)
            output_path = self.writer.write(processed) if write else None
            self._index_if_enabled(processed)
            results.append((processed, output_path))
        return results

    def process_url(
        self,
        url: str,
        *,
        category: DocumentCategory | None = None,
        write: bool = False,
    ) -> tuple[ProcessedDocument, Path | None]:
        raw_page = self.crawler.fetch(url)
        processed = self.process_raw_page(raw_page, category=category)

        output_path = self.writer.write(processed) if write else None
        self._index_if_enabled(processed)
        return processed, output_path

    def process_youtube_feed(
        self,
        feed_url: str,
        *,
        write: bool = False,
    ) -> list[tuple[ProcessedDocument, Path | None]]:
        raw_pages = self.youtube_extractor.fetch_feed(feed_url)
        return self.process_raw_pages(raw_pages, category=DocumentCategory.MULTIMEDIA, write=write)

    def process_news_feed(
        self,
        feed_url: str,
        *,
        write: bool = False,
    ) -> list[tuple[ProcessedDocument, Path | None]]:
        raw_pages = self.news_extractor.fetch_feed(feed_url)
        return self.process_raw_pages(raw_pages, category=DocumentCategory.NOTICIAS, write=write)

    def run_seed_urls(
        self,
        *,
        limit: int | None = None,
        write: bool = False,
    ) -> PipelineRunSummary:
        urls = [str(record.url) for record in build_seed_urls(self.settings.target_base_url)]
        if limit is not None:
            urls = urls[:limit]
        return self.run_urls(urls, write=write)

    def run_with_discovery(
        self,
        *,
        max_pages: int = 50,
        write: bool = False,
    ) -> PipelineRunSummary:
        """BFS crawl starting from seed URLs, following discovered internal links.

        Processes up to max_pages pages.  Blocked URLs (robots.txt) are silently
        skipped; other errors are recorded as failures in the summary.
        """
        summary = PipelineRunSummary(write_enabled=write)
        seed_urls = [str(r.url) for r in build_seed_urls(self.settings.target_base_url)]
        queue: list[str] = list(dict.fromkeys(seed_urls))
        seen: set[str] = set(queue)

        while queue and len(summary.results) < max_pages:
            url = queue.pop(0)
            try:
                logger.info("Discovering %s", url)
                raw_page = self.crawler.fetch(url)
                processed = self.process_raw_page(raw_page)
                output_path = self.writer.write(processed) if write else None
                summary.results.append(
                    self._build_success_result(
                        source_type="web_discovered",
                        input_reference=url,
                        processed=processed,
                        output_path=output_path,
                    )
                )
                if raw_page.html:
                    for link in extract_links(raw_page.html, url):
                        if link not in seen:
                            seen.add(link)
                            queue.append(link)
            except CrawlBlockedError:
                logger.info("Skipped (robots.txt): %s", url)
            except Exception as exc:
                logger.exception("Failed discovering %s", url)
                summary.results.append(
                    self._build_failure_result(
                        source_type="web_discovered",
                        input_reference=url,
                        error=exc,
                    )
                )

        return self._finalize_summary(summary)

    def run_urls(
        self,
        urls: list[str],
        *,
        write: bool = False,
        category: DocumentCategory | None = None,
    ) -> PipelineRunSummary:
        summary = PipelineRunSummary(write_enabled=write)
        for url in urls:
            try:
                logger.info("Processing web URL: %s", url)
                processed, output_path = self.process_url(url, category=category, write=write)
                summary.results.append(
                    self._build_success_result(
                        source_type="web",
                        input_reference=url,
                        processed=processed,
                        output_path=output_path,
                    )
                )
            except Exception as exc:
                logger.exception("Failed processing web URL: %s", url)
                summary.results.append(
                    self._build_failure_result(
                        source_type="web",
                        input_reference=url,
                        error=exc,
                    )
                )
        return self._finalize_summary(summary)

    def run_youtube_feeds(
        self,
        feed_urls: list[str],
        *,
        write: bool = False,
    ) -> PipelineRunSummary:
        summary = PipelineRunSummary(write_enabled=write)
        for feed_url in feed_urls:
            try:
                logger.info("Processing YouTube feed: %s", feed_url)
                for processed, output_path in self.process_youtube_feed(feed_url, write=write):
                    summary.results.append(
                        self._build_success_result(
                            source_type="youtube_feed",
                            input_reference=feed_url,
                            processed=processed,
                            output_path=output_path,
                        )
                    )
            except Exception as exc:
                logger.exception("Failed processing YouTube feed: %s", feed_url)
                summary.results.append(
                    self._build_failure_result(
                        source_type="youtube_feed",
                        input_reference=feed_url,
                        error=exc,
                    )
                )
        return self._finalize_summary(summary)

    def run_news_feeds(
        self,
        feed_urls: list[str],
        *,
        write: bool = False,
    ) -> PipelineRunSummary:
        summary = PipelineRunSummary(write_enabled=write)
        for feed_url in feed_urls:
            try:
                logger.info("Processing news feed: %s", feed_url)
                for processed, output_path in self.process_news_feed(feed_url, write=write):
                    summary.results.append(
                        self._build_success_result(
                            source_type="news_feed",
                            input_reference=feed_url,
                            processed=processed,
                            output_path=output_path,
                        )
                    )
            except Exception as exc:
                logger.exception("Failed processing news feed: %s", feed_url)
                summary.results.append(
                    self._build_failure_result(
                        source_type="news_feed",
                        input_reference=feed_url,
                        error=exc,
                    )
                )
        return self._finalize_summary(summary)

    def run_all(
        self,
        *,
        seed_limit: int | None = None,
        youtube_feed_urls: list[str] | None = None,
        news_feed_urls: list[str] | None = None,
        write: bool = False,
    ) -> PipelineRunSummary:
        summary = PipelineRunSummary(write_enabled=write)
        partials = [
            self.run_seed_urls(limit=seed_limit, write=write),
            self.run_youtube_feeds(youtube_feed_urls or [], write=write),
            self.run_news_feeds(news_feed_urls or [], write=write),
        ]

        for partial in partials:
            summary.results.extend(partial.results)

        return self._finalize_summary(summary)

    def save_summary(self, summary: PipelineRunSummary) -> Path:
        self.settings.resolved_runs_dir.mkdir(parents=True, exist_ok=True)
        timestamp = summary.started_at.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
        output_path = self.settings.resolved_runs_dir / f"run-summary-{timestamp}.json"
        output_path.write_text(summary.model_dump_json(indent=2), encoding="utf-8")
        return output_path

    @staticmethod
    def _build_success_result(
        *,
        source_type: str,
        input_reference: str,
        processed: ProcessedDocument,
        output_path: Path | None,
    ) -> PipelineItemResult:
        return PipelineItemResult(
            source_type=source_type,
            input_reference=input_reference,
            success=True,
            title=processed.document.title,
            category=processed.document.category.value,
            slug=processed.document.slug,
            output_path=str(output_path) if output_path is not None else None,
            warnings=processed.warnings,
        )

    @staticmethod
    def _build_failure_result(
        *,
        source_type: str,
        input_reference: str,
        error: Exception,
    ) -> PipelineItemResult:
        return PipelineItemResult(
            source_type=source_type,
            input_reference=input_reference,
            success=False,
            error=str(error),
        )

    @staticmethod
    def _finalize_summary(summary: PipelineRunSummary) -> PipelineRunSummary:
        summary.finished_at = datetime.now(UTC)
        return summary

    # ── Vectorstore helpers ──────────────────────────────────────

    def index_knowledge_dir(self) -> int:
        """Read all Markdown files from knowledge/ and index them in the vector store."""
        if self.vectorstore_writer is None:
            self.vectorstore_writer = VectorStoreWriter(settings=self.settings)

        knowledge_dir = self.settings.resolved_output_dir
        if not knowledge_dir.exists():
            logger.warning("Knowledge directory not found: %s", knowledge_dir)
            return 0

        count = 0
        for md_file in sorted(knowledge_dir.rglob("*.md")):
            try:
                processed = self._parse_markdown_file(md_file)
                if processed is not None:
                    self.vectorstore_writer.write(processed)
                    count += 1
            except Exception:
                logger.exception("Failed to index %s", md_file)

        logger.info("Indexed %d documents from %s", count, knowledge_dir)
        return count

    def search(self, query: str, n_results: int | None = None) -> list[SearchResult]:
        """Perform semantic search over the indexed knowledge."""
        if self.vectorstore_writer is None:
            self.vectorstore_writer = VectorStoreWriter(settings=self.settings)
        return self.vectorstore_writer.store.search(query, n_results=n_results)

    @staticmethod
    def _parse_markdown_file(path: Path) -> ProcessedDocument | None:
        """Parse a Markdown file with YAML front-matter into a ProcessedDocument."""
        text = path.read_text(encoding="utf-8")

        fm_match = re.match(r"^---\n(.+?)\n---\n\n?(.*)", text, re.DOTALL)
        if not fm_match:
            return None

        try:
            front = yaml.safe_load(fm_match.group(1))
        except Exception:
            return None

        if not isinstance(front, dict):
            return None

        body = fm_match.group(2).strip()
        doc_id = front.get("document_id", path.stem)
        title = front.get("title", path.stem)
        category_str = front.get("category", "01_organizacion")

        try:
            category = DocumentCategory(category_str)
        except ValueError:
            category = DocumentCategory.ORGANIZACION

        meta = ExtractionMetadata(
            source_url=front.get("source_url", "https://valledellili.org"),
            source_name=front.get("source_name", "Fundacion Valle del Lili"),
            extractor_name=front.get("extractor_name", "knowledge_indexer"),
        )

        source_doc = SourceDocument(
            document_id=doc_id,
            title=title,
            slug=front.get("slug", path.stem),
            category=category,
            source_url=front.get("source_url", "https://valledellili.org"),
            source_name=front.get("source_name", "Fundacion Valle del Lili"),
            summary=front.get("summary"),
            extraction_metadata=meta,
        )
        return ProcessedDocument(document=source_doc, content_markdown=body)
