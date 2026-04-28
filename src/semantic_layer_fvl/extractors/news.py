from __future__ import annotations

import email.utils
import xml.etree.ElementTree as ET

from semantic_layer_fvl.config import Settings, get_settings
from semantic_layer_fvl.extractors.http_client import HttpClient
from semantic_layer_fvl.schemas import ExtractionMetadata, RawPage


class NewsFeedExtractor:
    """Parses RSS or Atom feeds into RawPage records."""

    def __init__(
        self,
        client: HttpClient | None = None,
        *,
        settings: Settings | None = None,
        source_name: str = "News Feed",
    ) -> None:
        self.settings = settings or get_settings()
        self.client = client or HttpClient(self.settings)
        self.source_name = source_name

    def fetch_feed(self, feed_url: str) -> list[RawPage]:
        response = self.client.get(feed_url)
        response.raise_for_status()

        root = ET.fromstring(response.text)
        if self._local_name(root.tag) == "rss":
            return self._parse_rss(
                response.text,
                response.status_code,
                response.headers.get("content-type"),
            )
        return self._parse_atom(
            root, response.status_code, response.headers.get("content-type")
        )

    def _parse_rss(
        self, xml_text: str, status_code: int, content_type: str | None
    ) -> list[RawPage]:
        root = ET.fromstring(xml_text)
        channel = root.find("channel")
        if channel is None:
            return []

        source_name = self._find_text(channel, "title") or self.source_name
        items = channel.findall("item")
        pages: list[RawPage] = []

        for item in items[: self.settings.news_feed_limit]:
            link = self._find_text(item, "link")
            title = self._find_text(item, "title")
            if not link or not title:
                continue

            description = self._find_text(item, "description")
            published = self._normalize_datetime(self._find_text(item, "pubDate"))
            metadata = ExtractionMetadata(
                source_url=link,
                source_name=source_name,
                extractor_name="news_feed",
                http_status=status_code,
                content_type=content_type,
            )
            text_content = "\n\n".join(
                part for part in [title, description, published] if part
            )
            pages.append(
                RawPage(
                    url=link,
                    title=title,
                    text_content=text_content,
                    metadata=metadata,
                )
            )

        return pages

    def _parse_atom(
        self, root: ET.Element, status_code: int, content_type: str | None
    ) -> list[RawPage]:
        source_name = self._find_text_ns(root, "title") or self.source_name
        pages: list[RawPage] = []
        entries = [child for child in root if self._local_name(child.tag) == "entry"]

        for entry in entries[: self.settings.news_feed_limit]:
            title = self._find_text_ns(entry, "title")
            link = self._find_link_ns(entry)
            if not link or not title:
                continue

            summary = self._find_text_ns(entry, "summary") or self._find_text_ns(
                entry, "content"
            )
            published = self._find_text_ns(entry, "updated") or self._find_text_ns(
                entry, "published"
            )
            metadata = ExtractionMetadata(
                source_url=link,
                source_name=source_name,
                extractor_name="news_feed",
                http_status=status_code,
                content_type=content_type,
            )
            text_content = "\n\n".join(
                part for part in [title, summary, published] if part
            )
            pages.append(
                RawPage(
                    url=link,
                    title=title,
                    text_content=text_content,
                    metadata=metadata,
                )
            )

        return pages

    @staticmethod
    def _find_text(element: ET.Element, tag: str) -> str | None:
        found = element.find(tag)
        if found is None or found.text is None:
            return None
        text = found.text.strip()
        return text or None

    @classmethod
    def _find_text_ns(cls, element: ET.Element, local_name: str) -> str | None:
        for child in element:
            if cls._local_name(child.tag) == local_name and child.text:
                text = child.text.strip()
                if text:
                    return text
        return None

    @classmethod
    def _find_link_ns(cls, element: ET.Element) -> str | None:
        for child in element:
            if cls._local_name(child.tag) != "link":
                continue
            href = child.attrib.get("href")
            if href:
                return href
            if child.text and child.text.strip():
                return child.text.strip()
        return None

    @staticmethod
    def _local_name(tag: str) -> str:
        return tag.rsplit("}", 1)[-1]

    @staticmethod
    def _normalize_datetime(value: str | None) -> str | None:
        if not value:
            return None
        parsed = email.utils.parsedate_to_datetime(value)
        return parsed.isoformat() if parsed is not None else value
