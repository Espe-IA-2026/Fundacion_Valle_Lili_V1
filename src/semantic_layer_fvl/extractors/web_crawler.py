from __future__ import annotations

import logging
import re
from html.parser import HTMLParser
from typing import TYPE_CHECKING, cast
from urllib.parse import urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup
from markdownify import markdownify as md
from pydantic import AnyHttpUrl

from semantic_layer_fvl.config import Settings, get_settings
from semantic_layer_fvl.extractors.http_client import HttpClient
from semantic_layer_fvl.extractors.robots import RobotsPolicy
from semantic_layer_fvl.schemas import ExtractionMetadata, RawPage

if TYPE_CHECKING:
    from semantic_layer_fvl.domains import DomainConfig

_DOMAIN_NOISE_SELECTOR = (
    "nav, footer, header, aside, script, style, noscript, iframe, hr, "
    "figure, svg, img, "
    ".cnt_breadcrumbs, .social-share, "
    ".elementor-location-header, .elementor-location-footer"
)

logger = logging.getLogger(__name__)

_NON_HTML_EXTENSIONS = frozenset(
    {
        ".pdf",
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".svg",
        ".webp",
        ".ico",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        ".zip",
        ".rar",
        ".tar",
        ".gz",
        ".mp3",
        ".mp4",
        ".avi",
        ".mov",
        ".wmv",
        ".css",
        ".js",
        ".json",
        ".xml",
        ".rss",
        ".atom",
    }
)


class CrawlBlockedError(RuntimeError):
    """Raised when a URL is blocked by robots.txt rules."""


class _MetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._inside_title = False
        self.title_parts: list[str] = []
        self.meta_description: str | None = None
        self.og_title: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.lower()
        if lowered == "title":
            self._inside_title = True
            return
        if lowered != "meta":
            return

        attr_map = {key.lower(): value for key, value in attrs if value is not None}
        name = attr_map.get("name", "").lower()
        prop = attr_map.get("property", "").lower()
        content = attr_map.get("content")

        if content and prop == "og:title" and self.og_title is None:
            self.og_title = content.strip()

        if content and (name == "description" or prop == "og:description"):
            if self.meta_description is None:
                self.meta_description = content.strip()

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._inside_title = False

    def handle_data(self, data: str) -> None:
        if self._inside_title:
            cleaned = data.strip()
            if cleaned:
                self.title_parts.append(cleaned)


class _TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.primary_parts: list[str] = []
        self._ignored_depth = 0
        self._ignored_tags = {"head", "script", "style", "noscript", "svg", "title"}
        self._primary_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.lower()
        if lowered in self._ignored_tags:
            self._ignored_depth += 1
            return

        attr_map = {key.lower(): value for key, value in attrs if value is not None}
        if lowered in {"main", "article"} or attr_map.get("role", "").lower() == "main":
            self._primary_depth += 1

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered in self._ignored_tags and self._ignored_depth > 0:
            self._ignored_depth -= 1
            return

        if lowered in {"main", "article"} and self._primary_depth > 0:
            self._primary_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._ignored_depth > 0:
            return
        cleaned = " ".join(data.split())
        if cleaned:
            self.parts.append(cleaned)
            if self._primary_depth > 0:
                self.primary_parts.append(cleaned)


def extract_title(html: str) -> str | None:
    parser = _MetadataParser()
    parser.feed(html)
    if parser.og_title:
        return normalize_title(parser.og_title)
    if not parser.title_parts:
        return None
    return normalize_title(" ".join(parser.title_parts))


def extract_meta_description(html: str) -> str | None:
    parser = _MetadataParser()
    parser.feed(html)
    return parser.meta_description


def decode_html(response) -> str:
    content = response.content
    content_type = response.headers.get("content-type", "")

    encodings: list[str] = []
    charset_match = re.search(r"charset=([A-Za-z0-9._-]+)", content_type, re.IGNORECASE)
    if charset_match:
        encodings.append(charset_match.group(1).strip("\"'"))

    head_snippet = content[:4096].decode("latin-1", errors="ignore")
    meta_match = re.search(
        r"<meta[^>]+charset=['\"]?([A-Za-z0-9._-]+)",
        head_snippet,
        re.IGNORECASE,
    )
    if meta_match:
        encodings.append(meta_match.group(1))

    encodings.extend(["utf-8", "cp1252", "latin-1"])

    tried: set[str] = set()
    for encoding in encodings:
        normalized = encoding.lower()
        if normalized in tried:
            continue
        tried.add(normalized)
        try:
            return content.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue

    return response.text


def extract_text_content(html: str) -> tuple[str, bool]:
    """Return (text_content, has_primary_content).

    has_primary_content is True when content was found inside a <main>,
    <article> or role="main" element; False when falling back to all page text.
    """
    parser = _TextParser()
    parser.feed(html)
    has_primary = bool(parser.primary_parts)
    preferred_parts = parser.primary_parts if has_primary else parser.parts
    return "\n".join(preferred_parts), has_primary


class _LinkParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__()
        self._base_url = base_url
        self._base_domain = urlsplit(base_url).netloc.lower()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        for name, value in attrs:
            if name.lower() == "href" and value:
                link = self._normalize(value.strip())
                if link is not None:
                    self.links.append(link)

    def _normalize(self, href: str) -> str | None:
        if href.startswith(("#", "mailto:", "tel:", "javascript:")):
            return None
        absolute = urljoin(self._base_url, href)
        parts = urlsplit(absolute)
        if parts.scheme not in {"http", "https"}:
            return None
        if parts.netloc.lower() != self._base_domain:
            return None
        path_lower = parts.path.lower()
        # Skip non-Spanish language variants
        if path_lower == "/en" or path_lower.startswith("/en/"):
            return None
        for ext in _NON_HTML_EXTENSIONS:
            if path_lower.endswith(ext):
                return None
        path = parts.path.rstrip("/") or "/"
        return urlunsplit((parts.scheme, parts.netloc, path, "", ""))


def extract_links(html: str, base_url: str) -> list[str]:
    """Extract unique internal links from HTML, normalized and filtered.

    Returns absolute URLs belonging to the same domain as base_url,
    with fragments, query strings, and non-HTML resource extensions removed.
    """
    parser = _LinkParser(base_url)
    parser.feed(html)
    return list(dict.fromkeys(parser.links))


def normalize_title(value: str) -> str:
    normalized = re.sub(r"\s+", " ", value).strip()
    normalized = re.sub(r"([a-záéíóúñ])([A-ZÁÉÍÓÚÑ])", r"\1 \2", normalized)

    if "|" in normalized:
        first_part = normalized.split("|")[0].strip()
        if len(first_part) > 5:
            return first_part

    return normalized


class WebCrawler:
    """Minimal crawler for fetching a public page into the RawPage schema."""

    def __init__(
        self,
        client: HttpClient | None = None,
        *,
        settings: Settings | None = None,
        robots_policy: RobotsPolicy | None = None,
        source_name: str = "Fundacion Valle del Lili",
    ) -> None:
        self.settings = settings or get_settings()
        self.client = client or HttpClient(self.settings)
        self.robots_policy = robots_policy or RobotsPolicy(self.settings.user_agent)
        self.source_name = source_name

    _BROWSER_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
    }

    def fetch_domain_page(
        self, url: AnyHttpUrl, config: DomainConfig
    ) -> RawPage | None:
        """Fetch a page using domain-specific CSS selector and convert to Markdown.

        Uses browser-like headers to avoid 403 blocks, BeautifulSoup to find
        the domain container, and markdownify to produce structured Markdown.
        Falls back to <body> if the configured container selector is not found.
        Returns None only on network/HTTP errors.
        """
        import requests as req_lib

        self.client.rate_limiter.wait()
        try:
            response = req_lib.get(
                str(url),
                headers=self._BROWSER_HEADERS,
                timeout=self.settings.request_timeout,
            )
            response.raise_for_status()
        except Exception as exc:
            logger.warning("[domain_crawler] Could not fetch %s: %s", url, exc)
            return None

        soup = BeautifulSoup(response.content, "html.parser")

        for tag in soup.select(_DOMAIN_NOISE_SELECTOR):
            tag.decompose()

        container = soup.select_one(config.container_selector)
        if container is None:
            logger.warning(
                "[domain_crawler] Selector '%s' not found in %s — falling back to <body>",
                config.container_selector,
                url,
            )
            container = soup.body or soup

        markdown_content = md(
            str(container), heading_style="ATX", strip=["script", "style"]
        )
        markdown_content = re.sub(r'(?m)^(## )', r'---\n\n\1', markdown_content)
        markdown_content = re.sub(
            r'(?:---\n\n)?## Otros especialistas.*',
            '',
            markdown_content,
            flags=re.DOTALL | re.IGNORECASE,
        )
        markdown_content = re.sub(
            r'\[([^\]\n]+)\]\(https?://[^\)\n]+/buscador-integral/[^\)\n]*\)',
            r'\1',
            markdown_content,
        )
        markdown_content = markdown_content.strip()

        extra: dict[str, str] = {}
        for field_name, selector in config.extra_metadata_selectors.items():
            el = soup.select_one(selector)
            if el:
                extra[field_name] = el.get_text(separator=" ", strip=True)

        h1 = soup.find("h1")
        title_tag = soup.find("title")
        raw_title = h1 or title_tag
        title = raw_title.get_text(strip=True)[:200] if raw_title else str(url)

        return RawPage(
            url=url,
            title=title,
            html=response.text,
            text_content=markdown_content,
            markdown=markdown_content,
            extra_metadata=extra,
            metadata=ExtractionMetadata(
                source_url=cast(AnyHttpUrl, response.url),
                source_name=self.source_name,
                extractor_name="domain_web_crawler",
                http_status=response.status_code,
                content_type=response.headers.get("content-type"),
            ),
        )

    def fetch(self, url: AnyHttpUrl) -> RawPage:
        if self.settings.respect_robots_txt:
            decision = self.robots_policy.evaluate(str(url))
            if not decision.allowed:
                raise CrawlBlockedError(
                    f"URL blocked by robots policy: {url} ({decision.reason})"
                )

        response = self.client.get(str(url))
        response.raise_for_status()
        html = decode_html(response)
        meta_description = extract_meta_description(html)
        text_content, has_primary = extract_text_content(html)
        if meta_description and not has_primary:
            text_content = f"{meta_description}\n\n{text_content}".strip()

        source_url = cast(AnyHttpUrl, response.url)
        metadata = ExtractionMetadata(
            source_url=source_url,
            source_name=self.source_name,
            extractor_name="web_crawler",
            http_status=response.status_code,
            content_type=response.headers.get("content-type"),
        )
        return RawPage(
            url=source_url,
            title=extract_title(html),
            html=html,
            text_content=text_content,
            metadata=metadata,
        )
