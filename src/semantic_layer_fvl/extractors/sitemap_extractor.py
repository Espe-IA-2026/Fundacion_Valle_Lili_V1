from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING

import requests

if TYPE_CHECKING:
    from semantic_layer_fvl.domains import DomainConfig

logger = logging.getLogger(__name__)

_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
}

_SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def fetch_domain_urls(base_url: str, config: DomainConfig) -> list[str]:
    """Return filtered URLs from the domain sitemap.

    Tries each path in config.sitemap_paths with browser-like headers.
    Falls back to config.fallback_urls if all sitemaps fail.
    """
    base = base_url.rstrip("/")
    for path in config.sitemap_paths:
        urls = _parse_sitemap(f"{base}/{path}")
        if urls:
            filtered = _apply_filters(urls, config)
            logger.info("[sitemap] %s → %d URLs after filtering", path, len(filtered))
            return filtered
        logger.debug("[sitemap] %s/%s returned no URLs", base, path)

    logger.warning(
        "[sitemap] All sitemap paths failed for domain '%s' — using %d fallback URL(s)",
        config.name,
        len(config.fallback_urls),
    )
    return list(config.fallback_urls)


def _parse_sitemap(url: str) -> list[str]:
    try:
        resp = requests.get(url, headers=_BROWSER_HEADERS, timeout=20)
        if resp.status_code != 200:
            logger.debug("[sitemap] %s → HTTP %d", url, resp.status_code)
            return []
        root = ET.fromstring(resp.content)
        locs = root.findall(".//sm:url/sm:loc", _SITEMAP_NS)
        return [loc.text.strip() for loc in locs if loc.text]
    except requests.RequestException as exc:
        logger.debug("[sitemap] Network error for %s: %s", url, exc)
        return []
    except ET.ParseError as exc:
        logger.debug("[sitemap] XML parse error for %s: %s", url, exc)
        return []


def _apply_filters(urls: list[str], config: DomainConfig) -> list[str]:
    result: list[str] = []
    for url in urls:
        if config.url_include_patterns and not any(p in url for p in config.url_include_patterns):
            continue
        if any(p in url for p in config.url_exclude_patterns):
            continue
        result.append(url)
    return result
