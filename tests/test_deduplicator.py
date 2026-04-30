"""Tests para ContentDeduplicator: deduplicación por URL canónica y checksum."""

from __future__ import annotations

import pytest

from semantic_layer_fvl.processors.deduplicator import ContentDeduplicator


def test_first_url_not_duplicate() -> None:
    dedup = ContentDeduplicator()
    assert dedup.is_duplicate("https://example.com/page", None) is False


def test_same_url_is_duplicate() -> None:
    dedup = ContentDeduplicator()
    dedup.is_duplicate("https://example.com/page", None)
    assert dedup.is_duplicate("https://example.com/page", None) is True


def test_youtu_be_normalized_to_youtube_watch() -> None:
    dedup = ContentDeduplicator()
    dedup.is_duplicate("https://youtu.be/abc123", None)
    assert dedup.is_duplicate("https://www.youtube.com/watch?v=abc123", None) is True


def test_youtube_watch_then_youtu_be() -> None:
    dedup = ContentDeduplicator()
    dedup.is_duplicate("https://www.youtube.com/watch?v=xyz999", None)
    assert dedup.is_duplicate("https://youtu.be/xyz999", None) is True


def test_tracking_params_stripped() -> None:
    dedup = ContentDeduplicator()
    dedup.is_duplicate("https://example.com/article?utm_source=email&utm_medium=cpc", None)
    assert dedup.is_duplicate("https://example.com/article", None) is True


def test_fbclid_stripped() -> None:
    dedup = ContentDeduplicator()
    dedup.is_duplicate("https://example.com/page?fbclid=IwAR0xxx", None)
    assert dedup.is_duplicate("https://example.com/page", None) is True


def test_content_checksum_dedup() -> None:
    text = "Este es el contenido del artículo repetido."
    dedup = ContentDeduplicator()
    dedup.is_duplicate("https://source1.com/a", text)
    assert dedup.is_duplicate("https://source2.com/b", text) is True


def test_different_content_not_duplicate() -> None:
    dedup = ContentDeduplicator()
    dedup.is_duplicate("https://a.com/1", "Contenido A diferente aquí.")
    assert dedup.is_duplicate("https://b.com/2", "Contenido B totalmente distinto.") is False


def test_canonical_url_lowercase_scheme_host() -> None:
    canonical = ContentDeduplicator.canonical_url("HTTPS://Example.COM/Path")
    assert canonical.startswith("https://example.com")


def test_fragment_stripped() -> None:
    canonical = ContentDeduplicator.canonical_url("https://example.com/page#section")
    assert "#" not in canonical


def test_content_checksum_case_insensitive() -> None:
    c1 = ContentDeduplicator.content_checksum("Hola Mundo")
    c2 = ContentDeduplicator.content_checksum("hola mundo")
    assert c1 == c2


def test_content_checksum_whitespace_normalized() -> None:
    c1 = ContentDeduplicator.content_checksum("hola   mundo")
    c2 = ContentDeduplicator.content_checksum("hola mundo")
    assert c1 == c2
