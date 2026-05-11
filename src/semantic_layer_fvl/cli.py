"""Interfaz de linea de comandos para semantic_layer_fvl."""

from __future__ import annotations

import argparse

from semantic_layer_fvl.config import configure_logging, get_settings
from semantic_layer_fvl.extractors import build_seed_urls
from semantic_layer_fvl.orchestrator import SemanticPipeline


def build_parser() -> argparse.ArgumentParser:
    """Construye y devuelve el analizador de argumentos."""

    parser = argparse.ArgumentParser(
        prog="semantic-layer-fvl",
        description="Herramientas base del proyecto de capa semantica.",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser(
        "show-config",
        help="Muestra la configuracion cargada desde variables de entorno.",
    )
    subparsers.add_parser(
        "list-seeds",
        help="Lista las URLs semilla iniciales definidas para el sitio objetivo.",
    )
    crawl_once_parser = subparsers.add_parser(
        "crawl-once",
        help=(
            "Extrae una URL, la procesa y opcionalmente la escribe como " "Markdown."
        ),
    )
    crawl_once_parser.add_argument("url", help="URL publica a procesar.")
    crawl_once_parser.add_argument(
        "--write",
        action="store_true",
        help="Escribe el Markdown final en el directorio de salida.",
    )
    youtube_feed_parser = subparsers.add_parser(
        "youtube-feed",
        help="Procesa un feed Atom publico de YouTube.",
    )
    youtube_feed_parser.add_argument("feed_url", help="URL del feed Atom de YouTube.")
    youtube_feed_parser.add_argument(
        "--write",
        action="store_true",
        help="Escribe los documentos generados en el directorio de salida.",
    )
    news_feed_parser = subparsers.add_parser(
        "news-feed",
        help="Procesa un feed RSS o Atom de noticias.",
    )
    news_feed_parser.add_argument("feed_url", help="URL del feed RSS o Atom.")
    news_feed_parser.add_argument(
        "--write",
        action="store_true",
        help="Escribe los documentos generados en el directorio de salida.",
    )
    crawl_seeds_parser = subparsers.add_parser(
        "crawl-seeds",
        help="Procesa varias URLs semilla del sitio objetivo.",
    )
    crawl_seeds_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Cantidad maxima de semillas a procesar.",
    )
    crawl_seeds_parser.add_argument(
        "--write",
        action="store_true",
        help="Escribe los documentos generados en el directorio de salida.",
    )
    crawl_seeds_parser.add_argument(
        "--save-summary",
        action="store_true",
        help="Guarda el resumen de corrida en el directorio de runs.",
    )
    crawl_discover_parser = subparsers.add_parser(
        "crawl-discover",
        help=(
            "Rastrea el sitio descubriendo nuevos enlaces desde las " "semillas (BFS)."
        ),
    )
    crawl_discover_parser.add_argument(
        "--max-pages",
        type=int,
        default=50,
        help="Numero maximo de paginas a procesar (default: 50).",
    )
    crawl_discover_parser.add_argument(
        "--write",
        action="store_true",
        help="Escribe los documentos generados en el directorio de salida.",
    )
    crawl_discover_parser.add_argument(
        "--save-summary",
        action="store_true",
        help="Guarda el resumen de corrida en el directorio de runs.",
    )
    run_all_parser = subparsers.add_parser(
        "run-all",
        help=(
            "Ejecuta una corrida compuesta con semillas, feeds de YouTube "
            "y feeds de noticias."
        ),
    )
    run_all_parser.add_argument(
        "--seed-limit",
        type=int,
        default=None,
        help="Cantidad maxima de URLs semilla a procesar.",
    )
    run_all_parser.add_argument(
        "--youtube-feed",
        action="append",
        default=[],
        help="Feed de YouTube a incluir. Puede repetirse.",
    )
    run_all_parser.add_argument(
        "--news-feed",
        action="append",
        default=[],
        help="Feed de noticias a incluir. Puede repetirse.",
    )
    run_all_parser.add_argument(
        "--write",
        action="store_true",
        help="Escribe los documentos generados en el directorio de salida.",
    )
    run_all_parser.add_argument(
        "--save-summary",
        action="store_true",
        help="Guarda el resumen de corrida en el directorio de runs.",
    )
    youtube_search_parser = subparsers.add_parser(
        "youtube-search",
        help="Busca videos de YouTube por palabra clave y los procesa con metadatos enriquecidos.",
    )
    youtube_search_parser.add_argument(
        "query",
        nargs="+",
        help="Términos de búsqueda (pueden pasarse varios).",
    )
    youtube_search_parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Máximo de videos a procesar por query (default: 20).",
    )
    youtube_search_parser.add_argument(
        "--write",
        action="store_true",
        help="Escribe los documentos generados en el directorio de salida.",
    )
    youtube_search_parser.add_argument(
        "--save-summary",
        action="store_true",
        help="Guarda el resumen de corrida en el directorio de runs.",
    )
    news_curated_parser = subparsers.add_parser(
        "news-curated",
        help="Procesa feeds de noticias curados y Google News con deduplicación cross-source.",
    )
    news_curated_parser.add_argument(
        "--write",
        action="store_true",
        help="Escribe los documentos generados en el directorio de salida.",
    )
    news_curated_parser.add_argument(
        "--fetch-full",
        action="store_true",
        help="Descarga el cuerpo completo del artículo (más lento, más contenido).",
    )
    news_curated_parser.add_argument(
        "--save-summary",
        action="store_true",
        help="Guarda el resumen de corrida en el directorio de runs.",
    )
    crawl_domain_parser = subparsers.add_parser(
        "crawl-domain",
        help="Crawlea un dominio especifico usando su sitemap XML.",
    )
    crawl_domain_parser.add_argument(
        "domain",
        choices=["servicios", "especialistas", "sedes", "institucional"],
        help="Dominio a procesar.",
    )
    crawl_domain_parser.add_argument(
        "--max-urls",
        type=int,
        default=300,
        help="Limite de URLs a procesar (default: 300).",
    )
    crawl_domain_parser.add_argument(
        "--write",
        action="store_true",
        help="Escribe los documentos .md en el directorio de salida.",
    )
    crawl_domain_parser.add_argument(
        "--save-summary",
        action="store_true",
        help="Guarda el resumen de corrida en el directorio de runs.",
    )
    return parser


def handle_show_config() -> int:
    """Muestra la configuracion cargada desde variables de entorno."""

    settings = get_settings()
    print(f"project_name={settings.project_name}")
    print(f"target_base_url={settings.target_base_url}")
    print(f"knowledge_dir={settings.knowledge_dir}")
    print(f"request_interval_seconds={settings.request_interval_seconds}")
    print(f"respect_robots_txt={settings.respect_robots_txt}")
    return 0


def handle_list_seeds() -> int:
    """Lista las URLs semilla configuradas para el sitio objetivo."""

    settings = get_settings()
    for record in build_seed_urls(str(settings.target_base_url)):
        category = record.category.value if record.category else "sin_categoria"
        print(f"{record.priority:03d} {category} {record.url}")
    return 0


def handle_crawl_once(url: str, *, write: bool) -> int:
    """Procesa una URL publica y opcionalmente escribe Markdown."""

    pipeline = SemanticPipeline()
    processed, output_path = pipeline.process_url(url, write=write)

    print(f'title="{processed.document.title}"')
    print(f'category="{processed.document.category.value}"')
    print(f'slug="{processed.document.slug}"')
    print(f"headings={len(processed.headings)}")
    if output_path is not None:
        print(f'output_path="{output_path}"')
    return 0


def handle_youtube_feed(feed_url: str, *, write: bool) -> int:
    """Procesa un feed Atom publico de YouTube."""

    pipeline = SemanticPipeline()
    results = pipeline.process_youtube_feed(feed_url, write=write)

    print(f"documents={len(results)}")
    for processed, output_path in results[:3]:
        print(f'title="{processed.document.title}" slug="{processed.document.slug}"')
        if output_path is not None:
            print(f'output_path="{output_path}"')
    return 0


def handle_youtube_search(queries: list[str], *, limit: int, write: bool, save_summary: bool) -> int:
    """Busca videos de YouTube por palabra clave y los procesa con metadatos enriquecidos."""

    pipeline = SemanticPipeline()
    summary = pipeline.run_youtube_search(queries, limit_per_query=limit, write=write)
    summary_path = str(pipeline.save_summary(summary)) if save_summary else None
    print(f"queries={queries}")
    print_summary(summary, summary_path=summary_path)
    return 0 if summary.failure_count == 0 else 1


def handle_news_curated(*, write: bool, fetch_full: bool, save_summary: bool) -> int:
    """Procesa feeds de noticias curados y Google News con deduplicación cross-source."""

    pipeline = SemanticPipeline()
    summary = pipeline.run_curated_news(write=write, fetch_full=fetch_full)
    summary_path = str(pipeline.save_summary(summary)) if save_summary else None
    print_summary(summary, summary_path=summary_path)
    return 0 if summary.failure_count == 0 else 1


def handle_news_feed(feed_url: str, *, write: bool) -> int:
    """Procesa un feed RSS o Atom de noticias."""

    pipeline = SemanticPipeline()
    results = pipeline.process_news_feed(feed_url, write=write)

    print(f"documents={len(results)}")
    for processed, output_path in results[:3]:
        print(f'title="{processed.document.title}" slug="{processed.document.slug}"')
        if output_path is not None:
            print(f'output_path="{output_path}"')
    return 0


def print_summary(summary, *, summary_path: str | None = None) -> None:
    """Imprime un resumen compacto de una corrida."""

    print(f"processed={summary.processed_count}")
    print(f"success={summary.success_count}")
    print(f"failure={summary.failure_count}")
    if summary_path is not None:
        print(f'summary_path="{summary_path}"')

    for result in summary.results[:5]:
        status = "ok" if result.success else "error"
        line = (
            f'{status} source="{result.source_type}" input="{result.input_reference}"'
        )
        if result.title:
            line += f' title="{result.title}"'
        if result.output_path:
            line += f' output_path="{result.output_path}"'
        if result.error:
            line += f' error="{result.error}"'
        print(line)


def handle_crawl_domain(
    *,
    domain: str,
    max_urls: int,
    write: bool,
    save_summary: bool,
) -> int:
    """Crawlea un dominio especifico usando su sitemap XML."""

    pipeline = SemanticPipeline()
    summary = pipeline.run_domain(domain_name=domain, max_urls=max_urls, write=write)
    summary_path = str(pipeline.save_summary(summary)) if save_summary else None
    print(f"domain={domain}")
    print_summary(summary, summary_path=summary_path)
    return 0 if summary.failure_count == 0 else 1


def handle_crawl_discover(*, max_pages: int, write: bool, save_summary: bool) -> int:
    """Rastrea el sitio descubriendo nuevos enlaces desde semillas."""

    pipeline = SemanticPipeline()
    summary = pipeline.run_with_discovery(max_pages=max_pages, write=write)
    summary_path = str(pipeline.save_summary(summary)) if save_summary else None
    print_summary(summary, summary_path=summary_path)
    return 0 if summary.failure_count == 0 else 1


def handle_crawl_seeds(*, limit: int | None, write: bool, save_summary: bool) -> int:
    """Procesa las URLs semilla configuradas para el sitio objetivo."""

    pipeline = SemanticPipeline()
    summary = pipeline.run_seed_urls(limit=limit, write=write)
    summary_path = str(pipeline.save_summary(summary)) if save_summary else None
    print_summary(summary, summary_path=summary_path)
    return 0 if summary.failure_count == 0 else 1


def handle_run_all(
    *,
    seed_limit: int | None,
    youtube_feeds: list[str],
    news_feeds: list[str],
    write: bool,
    save_summary: bool,
) -> int:
    """Ejecuta una corrida compuesta con semillas y feeds."""

    pipeline = SemanticPipeline()
    summary = pipeline.run_all(
        seed_limit=seed_limit,
        youtube_feed_urls=youtube_feeds,
        news_feed_urls=news_feeds,
        write=write,
    )
    summary_path = str(pipeline.save_summary(summary)) if save_summary else None
    print_summary(summary, summary_path=summary_path)
    return 0 if summary.failure_count == 0 else 1


def main() -> int:
    """Punto de entrada de la CLI."""

    parser = build_parser()
    args = parser.parse_args()
    configure_logging()

    if args.command in (None, "show-config"):
        return handle_show_config()
    if args.command == "list-seeds":
        return handle_list_seeds()
    if args.command == "crawl-once":
        return handle_crawl_once(args.url, write=args.write)
    if args.command == "youtube-feed":
        return handle_youtube_feed(args.feed_url, write=args.write)
    if args.command == "youtube-search":
        return handle_youtube_search(
            args.query,
            limit=args.limit,
            write=args.write,
            save_summary=args.save_summary,
        )
    if args.command == "news-curated":
        return handle_news_curated(
            write=args.write,
            fetch_full=args.fetch_full,
            save_summary=args.save_summary,
        )
    if args.command == "news-feed":
        return handle_news_feed(args.feed_url, write=args.write)
    if args.command == "crawl-domain":
        return handle_crawl_domain(
            domain=args.domain,
            max_urls=args.max_urls,
            write=args.write,
            save_summary=args.save_summary,
        )
    if args.command == "crawl-discover":
        return handle_crawl_discover(
            max_pages=args.max_pages,
            write=args.write,
            save_summary=args.save_summary,
        )
    if args.command == "crawl-seeds":
        return handle_crawl_seeds(
            limit=args.limit,
            write=args.write,
            save_summary=args.save_summary,
        )
    if args.command == "run-all":
        return handle_run_all(
            seed_limit=args.seed_limit,
            youtube_feeds=args.youtube_feed,
            news_feeds=args.news_feed,
            write=args.write,
            save_summary=args.save_summary,
        )
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
