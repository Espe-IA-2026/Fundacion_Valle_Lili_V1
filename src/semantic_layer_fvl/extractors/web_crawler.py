from __future__ import annotations

import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit, urlunsplit

from semantic_layer_fvl.config import Settings, get_settings
from semantic_layer_fvl.extractors.http_client import HttpClient
from semantic_layer_fvl.extractors.robots import RobotsPolicy
from semantic_layer_fvl.schemas import ExtractionMetadata, RawPage

_NON_HTML_EXTENSIONS = frozenset(
    {
        ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".ico",
        ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
        ".zip", ".rar", ".tar", ".gz",
        ".mp3", ".mp4", ".avi", ".mov", ".wmv",
        ".css", ".js", ".json", ".xml", ".rss", ".atom",
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


class _MarkdownParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.primary_parts: list[str] = []
        
        self._ignored_depth = 0
        self._ignored_tags = {
            "head", "script", "style", "noscript", "svg", "title", 
            "nav", "footer", "iframe", "aside", "header", "form", "dialog"
        }
        self._primary_depth = 0
        self._base_url = ""
        self._link_urls: list[str | None] = []
        
        # State tracking for formatting
        self._list_depth = 0
        self._in_table = False
        self._in_th = False
        self._in_td = False
        
        self._table_headers: list[str] = []
        self._table_rows: list[list[str]] = []
        self._current_row: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.lower()
        if lowered in self._ignored_tags:
            self._ignored_depth += 1
            return

        attr_map = {key.lower(): value for key, value in attrs if value is not None}
        if lowered in {"main", "article"} or attr_map.get("role", "").lower() == "main":
            self._primary_depth += 1

        if self._ignored_depth > 0:
            return

        # Formatting
        if lowered in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            level = int(lowered[1])
            self._append_text(f"\n\n{'#' * level} ")
        elif lowered in {"p", "div", "br"}:
            self._append_text("\n\n")
        elif lowered == "a":
            href = attr_map.get("href", "").strip()
            if href and not href.startswith(("#", "javascript:", "mailto:", "tel:")):
                from urllib.parse import urljoin
                abs_url = urljoin(self._base_url, href)
                self._link_urls.append(abs_url)
                self._append_text("[")
            else:
                self._link_urls.append(None)
        elif lowered in {"ul", "ol"}:
            self._list_depth += 1
            self._append_text("\n")
        elif lowered == "li":
            indent = "  " * (self._list_depth - 1)
            self._append_text(f"\n{indent}- ")
        elif lowered == "table":
            self._in_table = True
            self._table_headers = []
            self._table_rows = []
        elif lowered == "tr":
            self._current_row = []
        elif lowered == "th":
            self._in_th = True
        elif lowered == "td":
            self._in_td = True

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        
        if lowered in self._ignored_tags and self._ignored_depth > 0:
            self._ignored_depth -= 1
            return

        if lowered in {"main", "article"} and self._primary_depth > 0:
            self._primary_depth -= 1
            
        if self._ignored_depth > 0:
            return

        # End Formatting
        if lowered in {"ul", "ol"}:
            self._list_depth -= 1
            self._append_text("\n\n")
        elif lowered == "a":
            if self._link_urls:
                url = self._link_urls.pop()
                if url:
                    # To avoid trailing spaces inside brackets breaking markdown:
                    # if self.parts and self.parts[-1].endswith(" "):
                    #    self.parts[-1] = self.parts[-1].rstrip()
                    # It's okay as is for now.
                    self._append_text(f"]({url})")
        elif lowered == "table":
            self._in_table = False
            self._render_table()
        elif lowered == "tr":
            if self._in_table and self._current_row:
                self._table_rows.append(self._current_row)
        elif lowered == "th":
            self._in_th = False
        elif lowered == "td":
            self._in_td = False

    def handle_data(self, data: str) -> None:
        if self._ignored_depth > 0:
            return
            
        cleaned = " ".join(data.split())
        if not cleaned:
            return

        if self._in_th:
            self._table_headers.append(cleaned)
        elif self._in_td:
            self._current_row.append(cleaned)
        else:
            self._append_text(cleaned + " ")

    def _append_text(self, text: str) -> None:
        # Don't add text if we are inside a table (it will be rendered at the end)
        if self._in_table:
            return
            
        if text.strip() == "" and self.parts and self.parts[-1].endswith("\n"):
            # Avoid excessive newlines
            if text == "\n\n" and self.parts[-1].endswith("\n\n"):
                return
                
        self.parts.append(text)
        if self._primary_depth > 0:
            self.primary_parts.append(text)

    def _render_table(self) -> None:
        if not self._table_headers and not self._table_rows:
            return
            
        table_md = "\n\n"
        
        # If no explicit headers were found, use the first row as headers or dummy headers
        headers = self._table_headers
        rows = self._table_rows
        
        if not headers and rows:
            headers = rows.pop(0)
            
        if headers:
            table_md += "| " + " | ".join(headers) + " |\n"
            table_md += "|" + "|".join(["---"] * len(headers)) + "|\n"
            
        for row in rows:
            # Pad row if it has fewer columns than headers
            padded_row = row + [""] * (len(headers) - len(row)) if headers else row
            table_md += "| " + " | ".join(padded_row) + " |\n"
            
        table_md += "\n"
        
        self.parts.append(table_md)
        if self._primary_depth > 0:
            self.primary_parts.append(table_md)

    def get_markdown(self, primary_only: bool) -> str:
        parts = self.primary_parts if primary_only else self.parts
        # Join parts and clean up excessive newlines
        md = "".join(parts)
        md = re.sub(r"\n{3,}", "\n\n", md)
        return md.strip()


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


def extract_text_content(html: str, base_url: str = "") -> tuple[str, bool]:
    """Return (text_content, has_primary_content).

    has_primary_content is True when content was found inside a <main>,
    <article> or role="main" element; False when falling back to all page text.
    """
    parser = _MarkdownParser()
    parser._base_url = base_url
    parser.feed(html)
    has_primary = bool(parser.primary_parts)
    return parser.get_markdown(has_primary), has_primary


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

    def fetch(self, url: str) -> RawPage:
        if self.settings.respect_robots_txt:
            decision = self.robots_policy.evaluate(url)
            if not decision.allowed:
                raise CrawlBlockedError(
                    f"URL blocked by robots policy: {url} ({decision.reason})"
                )

        response = self.client.get(url)
        response.raise_for_status()
        html = decode_html(response)
        meta_description = extract_meta_description(html)
        text_content, has_primary = extract_text_content(html, str(response.url))
        if meta_description and not has_primary:
            text_content = f"{meta_description}\n\n{text_content}".strip()

        metadata = ExtractionMetadata(
            source_url=str(response.url),
            source_name=self.source_name,
            extractor_name="web_crawler",
            http_status=response.status_code,
            content_type=response.headers.get("content-type"),
        )
        return RawPage(
            url=str(response.url),
            title=extract_title(html),
            html=html,
            text_content=text_content,
            metadata=metadata,
        )
