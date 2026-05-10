"""Pipeline de extremo a extremo: extracción, procesamiento y escritura de documentos Markdown."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from collections.abc import Sequence
from typing import Literal

from pydantic import AnyHttpUrl

from semantic_layer_fvl.config import Settings, get_settings
from semantic_layer_fvl.extractors.news import NewsFeedExtractor
from semantic_layer_fvl.extractors.site_map import build_seed_urls
from semantic_layer_fvl.extractors.web_crawler import (
    CrawlBlockedError,
    WebCrawler,
    extract_links,
)
from semantic_layer_fvl.extractors.youtube import YouTubeFeedExtractor
from semantic_layer_fvl.processors import SemanticStructurer, TextCleaner
from semantic_layer_fvl.schemas import (
    DocumentCategory,
    PipelineItemResult,
    PipelineRunSummary,
    ProcessedDocument,
    RawPage,
)
from semantic_layer_fvl.writers import MarkdownWriter

logger = logging.getLogger(__name__)


class SemanticPipeline:
    """Pipeline de extremo a extremo desde la extracción hasta la salida en Markdown."""

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
    ) -> None:
        """Inicializa las dependencias del pipeline; crea servicios por defecto si no se inyectan."""

        self.settings = settings or get_settings()
        self.crawler = crawler or WebCrawler(settings=self.settings)
        self.youtube_extractor = youtube_extractor or YouTubeFeedExtractor(
            settings=self.settings
        )
        self.news_extractor = news_extractor or NewsFeedExtractor(
            settings=self.settings
        )
        self.cleaner = cleaner or TextCleaner()
        self.structurer = structurer or SemanticStructurer()
        self.writer = writer or MarkdownWriter(self.settings)

    def process_raw_page(
        self,
        raw_page: RawPage,
        *,
        category: DocumentCategory | None = None,
    ) -> ProcessedDocument:
        """Limpia y estructura una página cruda en un documento procesado."""

        cleaned_text = self.cleaner.clean(raw_page.text_content)
        processed = self.structurer.build_document(
            raw_page, cleaned_text, category=category
        )
        if not cleaned_text:
            processed.warnings.append("empty_cleaned_text")
        return processed

    def process_raw_pages(
        self,
        raw_pages: list[RawPage],
        *,
        category: DocumentCategory | None = None,
        write: bool = False,
    ) -> list[tuple[ProcessedDocument, Path | None]]:
        """Procesa múltiples páginas crudas y opcionalmente escribe cada resultado."""

        results: list[tuple[ProcessedDocument, Path | None]] = []
        for raw_page in raw_pages:
            processed = self.process_raw_page(raw_page, category=category)
            output_path = self.writer.write(processed) if write else None
            results.append((processed, output_path))
        return results

    def process_url(
        self,
        url: str | AnyHttpUrl,
        *,
        category: DocumentCategory | None = None,
        write: bool = False,
    ) -> tuple[ProcessedDocument, Path | None]:
        """Obtiene una URL, la procesa y opcionalmente escribe el resultado."""

        raw_page = self.crawler.fetch(str(url))
        processed = self.process_raw_page(raw_page, category=category)

        output_path = self.writer.write(processed) if write else None
        return processed, output_path

    def process_youtube_feed(
        self,
        feed_url: str,
        *,
        write: bool = False,
    ) -> list[tuple[ProcessedDocument, Path | None]]:
        """Obtiene y procesa un feed Atom público de YouTube."""

        raw_pages = self.youtube_extractor.fetch_feed(feed_url)
        return self.process_raw_pages(
            raw_pages,
            category=DocumentCategory.MULTIMEDIA,
            write=write,
        )

    def process_news_feed(
        self,
        feed_url: str,
        *,
        write: bool = False,
    ) -> list[tuple[ProcessedDocument, Path | None]]:
        """Obtiene y procesa un feed RSS o Atom público de noticias."""

        raw_pages = self.news_extractor.fetch_feed(feed_url)
        return self.process_raw_pages(
            raw_pages,
            category=DocumentCategory.NOTICIAS,
            write=write,
        )

    def run_seed_urls(
        self,
        *,
        limit: int | None = None,
        write: bool = False,
    ) -> PipelineRunSummary:
        """Procesa las URLs semilla configuradas, opcionalmente limitadas por cantidad."""

        base_url = str(self.settings.target_base_url)
        urls = [str(record.url) for record in build_seed_urls(base_url)]
        if limit is not None:
            urls = urls[:limit]
        return self.run_urls(urls, write=write)

    def run_with_discovery(
        self,
        *,
        max_pages: int = 50,
        write: bool = False,
    ) -> PipelineRunSummary:
        """Ejecuta un rastreo BFS desde las semillas siguiendo los enlaces internos encontrados.

        Procesa hasta ``max_pages`` páginas. Las URLs bloqueadas se omiten y los demás
        errores se registran como fallos en el resumen de corrida.
        """

        summary = PipelineRunSummary(write_enabled=write)
        base_url = str(self.settings.target_base_url)
        seed_urls = [str(r.url) for r in build_seed_urls(base_url)]
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
                        input_reference=str(url),
                        processed=processed,
                        output_path=output_path,
                    )
                )
                if raw_page.html:
                    for link in extract_links(raw_page.html, str(url)):
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
                        input_reference=str(url),
                        error=exc,
                    )
                )

        return self._finalize_summary(summary)

    def run_urls(
        self,
        urls: Sequence[str | AnyHttpUrl],
        *,
        write: bool = False,
        category: DocumentCategory | None = None,
    ) -> PipelineRunSummary:
        """Procesa una lista de URLs web y recopila sus resultados en un resumen."""

        summary = PipelineRunSummary(write_enabled=write)
        for url in urls:
            try:
                logger.info("Processing web URL: %s", url)
                processed, output_path = self.process_url(
                    url, category=category, write=write
                )
                summary.results.append(
                    self._build_success_result(
                        source_type="web",
                        input_reference=str(url),
                        processed=processed,
                        output_path=output_path,
                    )
                )
            except Exception as exc:
                logger.exception("Failed processing web URL: %s", url)
                summary.results.append(
                    self._build_failure_result(
                        source_type="web",
                        input_reference=str(url),
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
        """Procesa múltiples feeds de YouTube y recopila sus resultados."""

        summary = PipelineRunSummary(write_enabled=write)
        for feed_url in feed_urls:
            try:
                logger.info("Processing YouTube feed: %s", feed_url)
                for processed, output_path in self.process_youtube_feed(
                    feed_url, write=write
                ):
                    summary.results.append(
                        self._build_success_result(
                            source_type="youtube_feed",
                            input_reference=str(feed_url),
                            processed=processed,
                            output_path=output_path,
                        )
                    )
            except Exception as exc:
                logger.exception("Failed processing YouTube feed: %s", feed_url)
                summary.results.append(
                    self._build_failure_result(
                        source_type="youtube_feed",
                        input_reference=str(feed_url),
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
        """Procesa múltiples feeds de noticias y recopila sus resultados."""

        summary = PipelineRunSummary(write_enabled=write)
        for feed_url in feed_urls:
            try:
                logger.info("Processing news feed: %s", feed_url)
                for processed, output_path in self.process_news_feed(
                    feed_url, write=write
                ):
                    summary.results.append(
                        self._build_success_result(
                            source_type="news_feed",
                            input_reference=str(feed_url),
                            processed=processed,
                            output_path=output_path,
                        )
                    )
            except Exception as exc:
                logger.exception("Failed processing news feed: %s", feed_url)
                summary.results.append(
                    self._build_failure_result(
                        source_type="news_feed",
                        input_reference=str(feed_url),
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
        """Ejecuta el pipeline completo: semillas, feeds de YouTube y feeds de noticias."""

        summary = PipelineRunSummary(write_enabled=write)
        partials = [
            self.run_seed_urls(limit=seed_limit, write=write),
            self.run_youtube_feeds(youtube_feed_urls or [], write=write),
            self.run_news_feeds(news_feed_urls or [], write=write),
        ]

        for partial in partials:
            summary.results.extend(partial.results)

        return self._finalize_summary(summary)

    def run_domain(
        self,
        domain_name: str,
        *,
        max_urls: int = 300,
        write: bool = False,
    ) -> PipelineRunSummary:
        """Rastrea un dominio configurado usando su sitemap XML.

        Por cada URL obtiene la página con el selector del dominio, construye
        el documento con la categoría del dominio y opcionalmente lo escribe
        en la subcarpeta correspondiente.
        """

        from semantic_layer_fvl.domains import DOMAIN_CONFIGS
        from semantic_layer_fvl.extractors.sitemap_extractor import fetch_domain_urls

        config = DOMAIN_CONFIGS.get(domain_name)
        if config is None:
            known = ", ".join(DOMAIN_CONFIGS)
            raise ValueError(f"Unknown domain '{domain_name}'. Valid options: {known}")

        base_url = str(self.settings.target_base_url).rstrip("/")
        urls = fetch_domain_urls(base_url, config)[:max_urls]
        logger.info(
            "[pipeline] Domain '%s': %d URL(s) to process",
            domain_name,
            len(urls),
        )

        summary = PipelineRunSummary(write_enabled=write)
        for url in urls:
            try:
                logger.info("[pipeline] %s -> %s", domain_name, url)
                raw_page = self.crawler.fetch_domain_page(url, config)
                if raw_page is None:
                    summary.results.append(
                        PipelineItemResult(
                            source_type="web_domain",
                            input_reference=str(url),
                            success=False,
                            error="fetch returned None (network or HTTP error)",
                        )
                    )
                    continue

                if not (raw_page.text_content or "").strip():
                    summary.results.append(
                        PipelineItemResult(
                            source_type="web_domain",
                            input_reference=str(url),
                            success=False,
                            error="empty content after extraction",
                        )
                    )
                    continue

                processed = self.structurer.build_document(
                    raw_page,
                    raw_page.text_content or "",
                    domain_name=domain_name,
                )
                output_path = (
                    self.writer.write(
                        processed,
                        domain_folder=config.output_folder,
                    )
                    if write
                    else None
                )
                summary.results.append(
                    self._build_success_result(
                        source_type="web_domain",
                        input_reference=str(url),
                        processed=processed,
                        output_path=output_path,
                    )
                )
            except Exception as exc:
                logger.exception("[pipeline] Error processing %s", url)
                summary.results.append(
                    self._build_failure_result(
                        source_type="web_domain",
                        input_reference=str(url),
                        error=exc,
                    )
                )

        return self._finalize_summary(summary)

    def save_summary(self, summary: PipelineRunSummary) -> Path:
        """Persiste un resumen de corrida en el directorio de runs como archivo JSON."""

        self.settings.resolved_runs_dir.mkdir(parents=True, exist_ok=True)
        timestamp = summary.started_at.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
        output_path = self.settings.resolved_runs_dir / f"run-summary-{timestamp}.json"
        output_path.write_text(summary.model_dump_json(indent=2), encoding="utf-8")
        return output_path

    def run_youtube_search(
        self,
        queries: list[str],
        *,
        limit_per_query: int = 20,
        write: bool = False,
    ) -> PipelineRunSummary:
        """Busca videos de YouTube por palabras clave y los procesa con metadatos enriquecidos.

        Usa ``yt-dlp`` para obtener título, descripción completa, duración y transcripción.
        Deduplica por URL canónica dentro de cada corrida.

        Args:
            queries: Lista de términos de búsqueda (p.ej. ``["Fundación Valle del Lili"]``).
            limit_per_query: Máximo de videos a procesar por query.
            write: Si es ``True`` escribe los documentos en disco.

        Returns:
            :class:`PipelineRunSummary` con los resultados de la corrida.
        """
        from semantic_layer_fvl.extractors.youtube_rich import YouTubeRichExtractor
        from semantic_layer_fvl.processors.deduplicator import ContentDeduplicator

        summary = PipelineRunSummary(write_enabled=write)
        extractor = YouTubeRichExtractor(settings=self.settings)
        dedup = ContentDeduplicator()

        for query in queries:
            try:
                video_urls = extractor.search_videos(query, limit=limit_per_query)
            except Exception as exc:
                logger.exception("[pipeline] Error buscando YouTube para query: %s", query)
                summary.results.append(
                    self._build_failure_result(
                        source_type="youtube_rich",
                        input_reference=f"ytsearch:{query}",
                        error=exc,
                    )
                )
                continue

            for video_url in video_urls:
                if dedup.is_duplicate(video_url, None):
                    logger.debug("[pipeline] Video duplicado, omitido: %s", video_url)
                    continue
                try:
                    logger.info("[pipeline] youtube_rich -> %s", video_url)
                    raw_page = extractor.fetch_video(video_url)
                    processed = self.structurer.build_document(
                        raw_page,
                        raw_page.text_content or "",
                        category=DocumentCategory.MULTIMEDIA,
                    )
                    output_path = self.writer.write(processed) if write else None
                    summary.results.append(
                        self._build_success_result(
                            source_type="youtube_rich",
                            input_reference=video_url,
                            processed=processed,
                            output_path=output_path,
                        )
                    )
                except Exception as exc:
                    logger.exception("[pipeline] Error procesando video: %s", video_url)
                    summary.results.append(
                        self._build_failure_result(
                            source_type="youtube_rich",
                            input_reference=video_url,
                            error=exc,
                        )
                    )

        return self._finalize_summary(summary)

    def run_curated_news(
        self,
        *,
        write: bool = False,
        fetch_full: bool = False,
    ) -> PipelineRunSummary:
        """Procesa feeds de noticias curados y Google News con deduplicación cross-source.

        Combina :data:`CURATED_NEWS_FEEDS` con feeds RSS de Google News generados
        por :class:`GoogleNewsFeedBuilder`. Deduplica por URL canónica y checksum
        de contenido para evitar duplicados entre fuentes.

        Args:
            write: Si es ``True`` escribe los documentos en disco.
            fetch_full: Si es ``True`` intenta descargar el cuerpo completo del artículo
                con :meth:`WebCrawler.fetch`. Aumenta la latencia considerablemente.

        Returns:
            :class:`PipelineRunSummary` con los resultados de la corrida.
        """
        from semantic_layer_fvl.extractors.google_news import GoogleNewsFeedBuilder
        from semantic_layer_fvl.news_feeds import CURATED_NEWS_FEEDS, is_fvl_relevant
        from semantic_layer_fvl.processors.cleaner import TextCleaner as _Cleaner
        from semantic_layer_fvl.processors.deduplicator import ContentDeduplicator
        from semantic_layer_fvl.processors.noise_presets import NEWS_NOISE

        summary = PipelineRunSummary(write_enabled=write)
        dedup = ContentDeduplicator()

        google_builder = GoogleNewsFeedBuilder(
            queries=self.settings.news_google_queries or None
        )
        feed_configs: list[tuple[str, str, frozenset[str], bool]] = [
            (f.url, f.name, f.extra_noise, f.requires_relevance_filter)
            for f in CURATED_NEWS_FEEDS
        ]
        for url in google_builder.feed_urls():
            # Google News ya viene pre-filtrado por la query → no aplicar filtro adicional
            feed_configs.append((url, "Google News — FVL", frozenset(), False))

        skipped_irrelevant = 0
        for feed_url, feed_name, extra_noise, needs_filter in feed_configs:
            try:
                self.news_extractor.source_name = feed_name
                raw_pages = self.news_extractor.fetch_feed(feed_url)
            except Exception as exc:
                logger.exception("[pipeline] Error obteniendo feed: %s", feed_url)
                summary.results.append(
                    self._build_failure_result(
                        source_type="news_curated",
                        input_reference=feed_url,
                        error=exc,
                    )
                )
                continue

            cleaner = _Cleaner(extra_noise=NEWS_NOISE | extra_noise)

            for raw_page in raw_pages:
                url_str = str(raw_page.url)

                if needs_filter and not is_fvl_relevant(
                    raw_page.title, raw_page.text_content
                ):
                    skipped_irrelevant += 1
                    continue

                if dedup.is_duplicate(url_str, raw_page.text_content):
                    logger.debug("[pipeline] Noticia duplicada, omitida: %s", url_str)
                    continue

                try:
                    if fetch_full:
                        full_text = self._fetch_article_body(url_str)
                        if full_text:
                            raw_page = raw_page.model_copy(
                                update={
                                    "text_content": (
                                        f"{raw_page.title}\n\n{full_text}"
                                    )
                                }
                            )

                    cleaned = cleaner.clean(raw_page.text_content or "")
                    processed = self.structurer.build_document(
                        raw_page, cleaned, category=DocumentCategory.NOTICIAS
                    )
                    output_path = self.writer.write(processed) if write else None
                    summary.results.append(
                        self._build_success_result(
                            source_type="news_curated",
                            input_reference=url_str,
                            processed=processed,
                            output_path=output_path,
                        )
                    )
                except Exception as exc:
                    logger.exception("[pipeline] Error procesando noticia: %s", url_str)
                    summary.results.append(
                        self._build_failure_result(
                            source_type="news_curated",
                            input_reference=url_str,
                            error=exc,
                        )
                    )

        if skipped_irrelevant:
            logger.info(
                "[pipeline] %d noticia(s) descartada(s) por no contener keywords FVL",
                skipped_irrelevant,
            )
        return self._finalize_summary(summary)

    def _fetch_article_body(self, url: str) -> str | None:
        """Descarga la URL y extrae el cuerpo del artículo con selectores genéricos.

        A diferencia de :meth:`WebCrawler.fetch` (que aplica selectores específicos
        de la FVL), este método busca selectores comunes de noticias (``<article>``,
        ``main``, ``[itemprop=articleBody]``) en cualquier medio externo.

        Args:
            url: URL del artículo a descargar.

        Returns:
            Cuerpo del artículo en texto plano (>200 chars) o ``None`` si no se
            puede extraer.
        """
        try:
            response = self.crawler.client.get(url)
            response.raise_for_status()
            html = response.text
        except Exception:
            return None

        from bs4 import BeautifulSoup

        try:
            soup = BeautifulSoup(html, "html.parser")
        except Exception:
            return None

        for tag_name in ("script", "style", "nav", "footer", "aside", "form"):
            for tag in soup.find_all(tag_name):
                tag.decompose()
        for selector in (
            ".related", ".share", ".comments", ".social", ".newsletter",
            ".advertisement", ".ad", "[class*='related']", "[class*='share']",
        ):
            for tag in soup.select(selector):
                tag.decompose()

        for selector in (
            "article",
            "[itemprop='articleBody']",
            ".article-body",
            ".article__body",
            ".entry-content",
            ".post-content",
            "main",
        ):
            elem = soup.select_one(selector)
            if elem:
                text = elem.get_text(separator="\n\n", strip=True)
                if len(text) > 200:
                    return text
        return None

    @staticmethod
    def _build_success_result(
        *,
        source_type: Literal[
            "web", "youtube_feed", "youtube_rich", "news_feed", "news_curated",
            "web_discovered", "web_domain",
        ],
        input_reference: str,
        processed: ProcessedDocument,
        output_path: Path | None,
    ) -> PipelineItemResult:
        """Construye un ``PipelineItemResult`` exitoso a partir de un documento procesado."""

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
        source_type: Literal[
            "web", "youtube_feed", "youtube_rich", "news_feed", "news_curated",
            "web_discovered", "web_domain",
        ],
        input_reference: str,
        error: Exception,
    ) -> PipelineItemResult:
        """Construye un ``PipelineItemResult`` de fallo con el mensaje de error capturado."""

        return PipelineItemResult(
            source_type=source_type,
            input_reference=input_reference,
            success=False,
            error=str(error),
        )

    @staticmethod
    def _finalize_summary(summary: PipelineRunSummary) -> PipelineRunSummary:
        """Registra la hora de finalización en el resumen y lo devuelve."""

        summary.finished_at = datetime.now(UTC)
        return summary
