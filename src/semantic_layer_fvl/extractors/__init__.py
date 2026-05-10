"""Submódulo de extractores: clientes HTTP, feeds, crawler web, YouTube enriquecido y Google News."""

from semantic_layer_fvl.extractors.google_news import GoogleNewsFeedBuilder
from semantic_layer_fvl.extractors.http_client import HttpClient, RateLimiter
from semantic_layer_fvl.extractors.news import NewsFeedExtractor
from semantic_layer_fvl.extractors.robots import (
    RobotsDecision,
    RobotsFetchResult,
    RobotsPolicy,
)
from semantic_layer_fvl.extractors.site_map import build_seed_urls
from semantic_layer_fvl.extractors.web_crawler import (
    CrawlBlockedError,
    WebCrawler,
    extract_links,
)
from semantic_layer_fvl.extractors.youtube import YouTubeFeedExtractor
from semantic_layer_fvl.extractors.youtube_rich import YouTubeRichExtractor

__all__ = [
    "CrawlBlockedError",
    "GoogleNewsFeedBuilder",
    "HttpClient",
    "NewsFeedExtractor",
    "RateLimiter",
    "RobotsDecision",
    "RobotsFetchResult",
    "RobotsPolicy",
    "WebCrawler",
    "YouTubeFeedExtractor",
    "YouTubeRichExtractor",
    "build_seed_urls",
    "extract_links",
]
