from __future__ import annotations

import httpx

from semantic_layer_fvl.config.settings import Settings
from semantic_layer_fvl.extractors import HttpClient, YouTubeFeedExtractor


def test_youtube_feed_extractor_parses_atom_entries() -> None:
    xml_feed = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom" xmlns:media="http://search.yahoo.com/mrss/">
      <title>YouTube channel</title>
      <entry>
        <title>Nuevo video institucional</title>
        <link rel="alternate" href="https://www.youtube.com/watch?v=abc123" />
        <published>2026-04-11T12:00:00+00:00</published>
        <author><name>Fundacion Valle del Lili</name></author>
        <media:group>
          <media:description>Resumen del video.</media:description>
        </media:group>
      </entry>
    </feed>
    """

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text=xml_feed,
            headers={"content-type": "application/atom+xml"},
            request=request,
        )

    settings = Settings(requests_per_second=10, youtube_search_limit=5)
    client = HttpClient(settings, transport=httpx.MockTransport(handler))
    extractor = YouTubeFeedExtractor(client, settings=settings)

    pages = extractor.fetch_feed("https://www.youtube.com/feeds/videos.xml?channel_id=test")
    client.close()

    assert len(pages) == 1
    assert str(pages[0].url) == "https://www.youtube.com/watch?v=abc123"
    assert "Resumen del video." in (pages[0].text_content or "")
    assert pages[0].metadata.extractor_name == "youtube_feed"
