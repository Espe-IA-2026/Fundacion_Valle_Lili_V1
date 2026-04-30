"""Submódulo de extractores: expone los clientes HTTP, parsers de feeds y el crawler web."""

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

__all__ = [
    "CrawlBlockedError",
    "HttpClient",
    "NewsFeedExtractor",
    "RateLimiter",
    "RobotsDecision",
    "RobotsFetchResult",
    "RobotsPolicy",
    "WebCrawler",
    "YouTubeFeedExtractor",
    "build_seed_urls",
    "extract_links",
]
