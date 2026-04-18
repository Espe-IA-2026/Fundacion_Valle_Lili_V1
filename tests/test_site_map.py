from __future__ import annotations

from semantic_layer_fvl.config.settings import Settings
from semantic_layer_fvl.extractors import build_seed_urls
from semantic_layer_fvl.schemas import DocumentCategory


def test_build_seed_urls_returns_prioritized_records() -> None:
    records = build_seed_urls("https://valledellili.org")

    assert len(records) >= 10
    assert str(records[0].url) == "https://valledellili.org/"
    assert records[0].category == DocumentCategory.ORGANIZACION
    assert any(str(record.url).endswith("/noticias-y-eventos") for record in records)


def test_build_seed_urls_accepts_settings_base_url() -> None:
    settings = Settings()

    records = build_seed_urls(settings.target_base_url)

    assert str(records[1].url).endswith("/nuestra-institucion")
