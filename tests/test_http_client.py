from __future__ import annotations

import httpx

from semantic_layer_fvl.config.settings import Settings
from semantic_layer_fvl.extractors.http_client import HttpClient, RateLimiter


class FakeClock:
    def __init__(self) -> None:
        self.current = 100.0
        self.sleeps: list[float] = []

    def time(self) -> float:
        return self.current

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.current += seconds


def test_rate_limiter_waits_for_remaining_interval() -> None:
    clock = FakeClock()
    limiter = RateLimiter(
        requests_per_second=0.5,
        time_provider=clock.time,
        sleeper=clock.sleep,
    )

    limiter.wait()
    limiter.wait()

    assert clock.sleeps == [2.0]


def test_http_client_sends_browser_like_headers() -> None:
    captured_headers: list[httpx.Headers] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_headers.append(request.headers)
        return httpx.Response(200, text="ok", request=request)

    settings = Settings(
        user_agent="semantic-layer-fvl-test",
        accept_language="es-CO,es;q=0.9",
        requests_per_second=10,
    )
    client = HttpClient(settings, transport=httpx.MockTransport(handler))
    response = client.get("https://valledellili.org/test")
    client.close()

    assert response.status_code == 200
    assert captured_headers[0].get("User-Agent") == "semantic-layer-fvl-test"
    assert "text/html" in (captured_headers[0].get("Accept") or "")
    assert captured_headers[0].get("Accept-Language") == "es-CO,es;q=0.9"
