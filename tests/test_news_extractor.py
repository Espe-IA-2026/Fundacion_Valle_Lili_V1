from __future__ import annotations

import httpx

from semantic_layer_fvl.config.settings import Settings
from semantic_layer_fvl.extractors import HttpClient, NewsFeedExtractor


def test_news_feed_extractor_parses_rss_items() -> None:
    rss_feed = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
      <channel>
        <title>Noticias FVL</title>
        <item>
          <title>Nuevo reconocimiento</title>
          <link>https://example.com/noticias/reconocimiento</link>
          <description>La fundacion recibe un nuevo reconocimiento.</description>
          <pubDate>Fri, 11 Apr 2026 12:00:00 GMT</pubDate>
        </item>
      </channel>
    </rss>
    """

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text=rss_feed,
            headers={"content-type": "application/rss+xml"},
            request=request,
        )

    settings = Settings(requests_per_second=10, news_feed_limit=10, news_search_days=10)
    client = HttpClient(settings, transport=httpx.MockTransport(handler))
    extractor = NewsFeedExtractor(client, settings=settings)

    pages = extractor.fetch_feed("https://example.com/feed.xml")
    client.close()

    assert len(pages) == 1
    assert str(pages[0].url) == "https://example.com/noticias/reconocimiento"
    assert pages[0].metadata.source_name == "Noticias FVL"
    assert "2026-04-11T12:00:00+00:00" in (pages[0].text_content or "")
