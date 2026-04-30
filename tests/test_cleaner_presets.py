"""Tests para presets de ruido en TextCleaner y constructor configurable."""

from __future__ import annotations

import pytest

from semantic_layer_fvl.processors.cleaner import TextCleaner
from semantic_layer_fvl.processors.noise_presets import NEWS_NOISE, WEB_FVL_NOISE, YOUTUBE_NOISE


def test_base_noise_still_filtered_without_extra() -> None:
    cleaner = TextCleaner()
    result = cleaner.clean("menu\nContenido real aquí.")
    assert "menu" not in result
    assert "Contenido real aquí." in result


def test_extra_noise_merged_with_base() -> None:
    cleaner = TextCleaner(extra_noise=NEWS_NOISE)
    result = cleaner.clean("lee también\nNoticias sobre la FVL.")
    assert "lee también" not in result
    assert "Noticias sobre la FVL." in result


def test_news_noise_preset_does_not_affect_default_cleaner() -> None:
    cleaner_default = TextCleaner()
    result = cleaner_default.clean("lee también\nContenido importante.")
    assert "lee también" in result


def test_youtube_noise_removed_when_preset_applied() -> None:
    cleaner = TextCleaner(extra_noise=YOUTUBE_NOISE)
    result = cleaner.clean("Suscríbete\nActiva la campanita\nContenido médico relevante.")
    assert "Suscríbete" not in result
    assert "Activa la campanita" not in result
    assert "Contenido médico relevante." in result


def test_extra_noise_case_insensitive_via_is_noise() -> None:
    cleaner = TextCleaner(extra_noise=frozenset({"suscríbete"}))
    result = cleaner.clean("Suscríbete\nTexto importante.")
    assert "Suscríbete" not in result


def test_news_noise_preset_exported_correctly() -> None:
    assert "lee también" in NEWS_NOISE
    assert "compartir" in NEWS_NOISE
    assert "suscríbete" in NEWS_NOISE


def test_youtube_noise_preset_exported_correctly() -> None:
    assert "suscríbete" in YOUTUBE_NOISE
    assert "activa la campanita" in YOUTUBE_NOISE


def test_web_fvl_noise_preset_exported_correctly() -> None:
    assert "menu" in WEB_FVL_NOISE
    assert "facebook" in WEB_FVL_NOISE


def test_none_extra_noise_same_as_default() -> None:
    c1 = TextCleaner()
    c2 = TextCleaner(extra_noise=None)
    text = "facebook\nContenido importante aquí."
    assert c1.clean(text) == c2.clean(text)


def test_multiple_presets_combined() -> None:
    combined = NEWS_NOISE | YOUTUBE_NOISE
    cleaner = TextCleaner(extra_noise=combined)
    result = cleaner.clean("lee también\nActiva la campanita\nInformación médica de la FVL.")
    assert "lee también" not in result
    assert "Activa la campanita" not in result
    assert "Información médica de la FVL." in result
