"""Tests para limpieza de HTML embebido en feeds RSS y filtrado de relevancia FVL."""

from __future__ import annotations

from semantic_layer_fvl.extractors.news import _strip_html
from semantic_layer_fvl.news_feeds import is_fvl_relevant


def test_strip_html_removes_p_tags() -> None:
    raw = "<p>Hola <strong>mundo</strong></p>"
    assert _strip_html(raw) == "Hola mundo"


def test_strip_html_removes_anchors_keeping_text() -> None:
    raw = '<p>Lee <a href="https://x.com">aquí</a> el artículo.</p>'
    result = _strip_html(raw)
    assert result == "Lee aquí el artículo."


def test_strip_html_collapses_whitespace() -> None:
    raw = "Texto    con   múltiples\n\nespacios"
    assert _strip_html(raw) == "Texto con múltiples espacios"


def test_strip_html_returns_none_for_empty() -> None:
    assert _strip_html(None) is None
    assert _strip_html("") in (None, "")


def test_strip_html_passthrough_when_no_tags() -> None:
    raw = "Texto plano sin etiquetas"
    assert _strip_html(raw) == "Texto plano sin etiquetas"


def test_strip_html_handles_nested_tags() -> None:
    # En RSS real el XML parser ya elimina el wrapper CDATA,
    # llegando aquí directamente las etiquetas HTML internas.
    raw = "<p>Resumen <em>importante</em> con <strong>énfasis</strong></p>"
    result = _strip_html(raw)
    assert "Resumen" in result
    assert "importante" in result
    assert "énfasis" in result
    assert "<" not in result


def test_is_fvl_relevant_matches_full_name() -> None:
    assert is_fvl_relevant("Noticia sobre la Fundación Valle del Lili", None)


def test_is_fvl_relevant_matches_acronym() -> None:
    assert is_fvl_relevant("La FVL inauguró nueva sede", None)


def test_is_fvl_relevant_matches_short_form() -> None:
    assert is_fvl_relevant("Hospital Valle del Lili anuncia", None)


def test_is_fvl_relevant_returns_false_for_unrelated() -> None:
    assert not is_fvl_relevant("Noticia general de salud", "Sin relación con la institución")


def test_is_fvl_relevant_handles_none_inputs() -> None:
    assert not is_fvl_relevant(None, None)


def test_is_fvl_relevant_case_insensitive() -> None:
    assert is_fvl_relevant("FUNDACIÓN valle DEL lili", None)


def test_is_fvl_relevant_searches_in_body_too() -> None:
    assert is_fvl_relevant("Salud en Cali", "El hospital Valle del Lili abrió nueva sede")
