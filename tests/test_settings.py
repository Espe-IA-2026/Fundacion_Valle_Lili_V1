from semantic_layer_fvl.config.settings import Settings


def test_request_interval_is_derived_from_requests_per_second() -> None:
    settings = Settings(requests_per_second=0.5)
    assert settings.request_interval_seconds == 2.0
