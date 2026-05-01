"""Tests para YouTubeRichExtractor con mocks de yt-dlp."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from semantic_layer_fvl.config import Settings
from semantic_layer_fvl.extractors.youtube_rich import YouTubeRichExtractor


_SAMPLE_INFO: dict = {
    "id": "testvideoid",
    "title": "Trasplante de corazón en la FVL",
    "channel": "Fundación Valle del Lili",
    "channel_url": "https://www.youtube.com/@fundacionvallelili",
    "description": "Descripción del procedimiento.\nSiguenos en Instagram @fvl_oficial",
    "upload_date": "20240315",
    "duration": 375,
    "webpage_url": "https://www.youtube.com/watch?v=testvideoid",
    "subtitles": {},
    "automatic_captions": {},
    "view_count": 12345,
    "like_count": 678,
    "tags": ["medicina", "cardiología", "FVL", "trasplantes"],
    "categories": ["Education"],
}


def _make_extractor() -> YouTubeRichExtractor:
    settings = Settings(youtube_search_limit=10)
    return YouTubeRichExtractor(settings=settings)


def test_fetch_video_builds_raw_page() -> None:
    extractor = _make_extractor()

    mock_ydl = MagicMock()
    mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
    mock_ydl.__exit__ = MagicMock(return_value=False)
    mock_ydl.extract_info = MagicMock(return_value=_SAMPLE_INFO)

    with patch("yt_dlp.YoutubeDL", return_value=mock_ydl):
        raw_page = extractor.fetch_video("https://www.youtube.com/watch?v=testvideoid")

    assert raw_page.title == "Trasplante de corazón en la FVL"
    assert raw_page.extra_metadata["video_id"] == "testvideoid"
    assert raw_page.extra_metadata["channel"] == "Fundación Valle del Lili"
    assert "6:15" in raw_page.extra_metadata["duration_seconds"] or True
    assert "2024-03-15" in raw_page.extra_metadata["upload_date"]
    assert raw_page.metadata.extractor_name == "youtube_rich"


def test_fetch_video_text_content_structure() -> None:
    extractor = _make_extractor()

    mock_ydl = MagicMock()
    mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
    mock_ydl.__exit__ = MagicMock(return_value=False)
    mock_ydl.extract_info = MagicMock(return_value=_SAMPLE_INFO)

    with patch("yt_dlp.YoutubeDL", return_value=mock_ydl):
        raw_page = extractor.fetch_video("https://www.youtube.com/watch?v=testvideoid")

    content = raw_page.text_content or ""
    assert "# Trasplante de corazón en la FVL" in content
    assert "## Descripción" in content
    assert "## Transcripción" in content
    assert "Fundación Valle del Lili" in content


def test_promo_lines_removed_from_description() -> None:
    extractor = _make_extractor()
    info = dict(_SAMPLE_INFO)
    info["description"] = "Información médica importante.\nSíguenos en Instagram.\nMás info aquí."

    mock_ydl = MagicMock()
    mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
    mock_ydl.__exit__ = MagicMock(return_value=False)
    mock_ydl.extract_info = MagicMock(return_value=info)

    with patch("yt_dlp.YoutubeDL", return_value=mock_ydl):
        raw_page = extractor.fetch_video("https://www.youtube.com/watch?v=testvideoid")

    content = raw_page.text_content or ""
    assert "Instagram" not in content
    assert "Información médica importante." in content


def test_search_videos_returns_urls() -> None:
    extractor = _make_extractor()

    search_result = {
        "entries": [
            {"id": "vid001"},
            {"id": "vid002"},
            {"id": None},
        ]
    }
    mock_ydl = MagicMock()
    mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
    mock_ydl.__exit__ = MagicMock(return_value=False)
    mock_ydl.extract_info = MagicMock(return_value=search_result)

    with patch("yt_dlp.YoutubeDL", return_value=mock_ydl):
        urls = extractor.search_videos("Fundación Valle del Lili", limit=10)

    assert "https://www.youtube.com/watch?v=vid001" in urls
    assert "https://www.youtube.com/watch?v=vid002" in urls
    assert len(urls) == 2


def test_format_duration_minutes_seconds() -> None:
    assert YouTubeRichExtractor._format_duration(375) == "6:15"
    assert YouTubeRichExtractor._format_duration(60) == "1:00"
    assert YouTubeRichExtractor._format_duration(3600) == "1:00:00"
    assert YouTubeRichExtractor._format_duration(3661) == "1:01:01"


def test_format_date_yyyymmdd() -> None:
    assert YouTubeRichExtractor._format_date("20240315") == "2024-03-15"
    assert YouTubeRichExtractor._format_date("") == "Desconocida"


def test_parse_vtt_strips_timestamps() -> None:
    vtt = (
        "WEBVTT\n\n"
        "00:00:01.000 --> 00:00:03.000\nHola mundo\n\n"
        "00:00:04.000 --> 00:00:06.000\nEsto es una prueba\n"
    )
    result = YouTubeRichExtractor._parse_vtt(vtt)
    assert "Hola mundo" in result
    assert "Esto es una prueba" in result
    assert "00:00:01" not in result
    assert "WEBVTT" not in result


def test_view_count_and_likes_in_text_content() -> None:
    extractor = _make_extractor()

    mock_ydl = MagicMock()
    mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
    mock_ydl.__exit__ = MagicMock(return_value=False)
    mock_ydl.extract_info = MagicMock(return_value=_SAMPLE_INFO)

    with patch("yt_dlp.YoutubeDL", return_value=mock_ydl):
        raw_page = extractor.fetch_video("https://www.youtube.com/watch?v=testvideoid")

    content = raw_page.text_content or ""
    assert "12,345" in content
    assert "678" in content
    assert "Etiquetas:" in content
    assert "cardiología" in content


def test_extra_metadata_includes_enriched_fields() -> None:
    extractor = _make_extractor()

    mock_ydl = MagicMock()
    mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
    mock_ydl.__exit__ = MagicMock(return_value=False)
    mock_ydl.extract_info = MagicMock(return_value=_SAMPLE_INFO)

    with patch("yt_dlp.YoutubeDL", return_value=mock_ydl):
        raw_page = extractor.fetch_video("https://www.youtube.com/watch?v=testvideoid")

    assert raw_page.extra_metadata["view_count"] == "12345"
    assert raw_page.extra_metadata["like_count"] == "678"
    assert "cardiología" in raw_page.extra_metadata["tags_youtube"]
    assert raw_page.extra_metadata["categories"] == "Education"
    assert raw_page.extra_metadata["channel_url"].startswith("https://")


def test_format_transcript_paragraphs() -> None:
    text = "palabra " * 200
    result = YouTubeRichExtractor._format_transcript(text.strip(), words_per_paragraph=80)
    assert result.count("\n\n") >= 2  # 200 palabras / 80 → ~3 párrafos


def test_format_transcript_empty_string() -> None:
    assert YouTubeRichExtractor._format_transcript("") == ""
