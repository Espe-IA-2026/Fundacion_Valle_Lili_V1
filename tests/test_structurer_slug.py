"""Tests para resolución de slug en SemanticStructurer (especialmente YouTube)."""

from __future__ import annotations

from pydantic import HttpUrl

from semantic_layer_fvl.processors.structurer import SemanticStructurer
from semantic_layer_fvl.schemas import ExtractionMetadata, RawPage


def _make_raw_page(
    url: str,
    *,
    title: str = "Documento de prueba",
    extra_metadata: dict[str, str] | None = None,
) -> RawPage:
    metadata = ExtractionMetadata(
        source_url=HttpUrl(url),
        source_name="Test",
        extractor_name="test_extractor",
    )
    return RawPage(
        url=HttpUrl(url),
        title=title,
        text_content="Contenido de prueba.",
        metadata=metadata,
        extra_metadata=extra_metadata or {},
    )


def test_youtube_slug_uses_video_id_from_extra_metadata() -> None:
    raw = _make_raw_page(
        "https://www.youtube.com/watch?v=ABC123xyz",
        title="Video FVL",
        extra_metadata={"video_id": "ABC123xyz"},
    )
    slug = SemanticStructurer._resolve_slug(raw, "Video FVL")
    assert slug == "abc123xyz"


def test_youtube_slug_falls_back_to_query_param_when_no_metadata() -> None:
    raw = _make_raw_page(
        "https://www.youtube.com/watch?v=DEF456",
        title="Video sin metadata",
    )
    slug = SemanticStructurer._resolve_slug(raw, "Video sin metadata")
    assert slug == "def456"


def test_youtube_slug_handles_youtu_be_short_url() -> None:
    raw = _make_raw_page(
        "https://youtu.be/GHI789",
        title="Video corto",
        extra_metadata={"video_id": "GHI789"},
    )
    slug = SemanticStructurer._resolve_slug(raw, "Video corto")
    assert slug == "ghi789"


def test_two_youtube_videos_get_different_slugs() -> None:
    raw1 = _make_raw_page(
        "https://www.youtube.com/watch?v=video1",
        extra_metadata={"video_id": "video1"},
    )
    raw2 = _make_raw_page(
        "https://www.youtube.com/watch?v=video2",
        extra_metadata={"video_id": "video2"},
    )
    slug1 = SemanticStructurer._resolve_slug(raw1, "Title 1")
    slug2 = SemanticStructurer._resolve_slug(raw2, "Title 2")
    assert slug1 != slug2
    assert slug1 == "video1"
    assert slug2 == "video2"


def test_external_id_priority_over_video_id() -> None:
    # video_id se busca primero por orden en el código
    raw = _make_raw_page(
        "https://www.youtube.com/watch?v=videoid",
        extra_metadata={"video_id": "videoid", "external_id": "otherid"},
    )
    slug = SemanticStructurer._resolve_slug(raw, "T")
    assert slug == "videoid"


def test_external_id_used_when_no_video_id() -> None:
    raw = _make_raw_page(
        "https://example.com/article",
        extra_metadata={"external_id": "guid-12345"},
    )
    slug = SemanticStructurer._resolve_slug(raw, "T")
    assert slug == "guid-12345"


def test_normal_url_uses_last_path_segment() -> None:
    raw = _make_raw_page("https://example.com/section/article-name")
    slug = SemanticStructurer._resolve_slug(raw, "Article Name")
    assert slug == "article-name"


def test_generic_segment_falls_back_to_title() -> None:
    raw = _make_raw_page("https://example.com/watch")
    slug = SemanticStructurer._resolve_slug(raw, "Mi Título")
    assert slug == "mi-titulo"


def test_root_url_uses_title_slug() -> None:
    raw = _make_raw_page("https://example.com/", title="Inicio")
    slug = SemanticStructurer._resolve_slug(raw, "Inicio")
    assert slug == "inicio"
