"""Tests para GoogleNewsFeedBuilder: construcción de URLs RSS de Google News."""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest

from semantic_layer_fvl.extractors.google_news import GoogleNewsFeedBuilder


def test_feed_urls_returns_one_per_query() -> None:
    builder = GoogleNewsFeedBuilder(queries=["FVL", "Hospital Cali"])
    urls = builder.feed_urls()
    assert len(urls) == 2


def test_url_contains_encoded_query() -> None:
    builder = GoogleNewsFeedBuilder(queries=["Fundación Valle del Lili"])
    url = builder.feed_urls()[0]
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    assert "q" in qs
    assert "Fundación Valle del Lili" in qs["q"][0]


def test_url_locale_params_present() -> None:
    builder = GoogleNewsFeedBuilder(queries=["FVL"])
    url = builder.feed_urls()[0]
    assert "hl=es-419" in url
    assert "gl=CO" in url
    assert "ceid=CO:es" in url


def test_url_points_to_google_news() -> None:
    builder = GoogleNewsFeedBuilder(queries=["FVL"])
    url = builder.feed_urls()[0]
    assert url.startswith("https://news.google.com/rss/search")


def test_default_queries_used_when_none_provided() -> None:
    builder = GoogleNewsFeedBuilder()
    urls = builder.feed_urls()
    assert len(urls) >= 1
    assert all(url.startswith("https://news.google.com/") for url in urls)


def test_query_with_spaces_encoded_correctly() -> None:
    builder = GoogleNewsFeedBuilder(queries=["Hospital Valle del Lili"])
    url = builder.feed_urls()[0]
    assert " " not in url
    assert "Hospital" in url
