"""Tests para la lógica de reintentos con backoff exponencial en HttpClient."""

from __future__ import annotations

import httpx
import pytest

from semantic_layer_fvl.extractors.http_client import HttpClient, RateLimiter
from semantic_layer_fvl.config import Settings


def _instant_rate_limiter() -> RateLimiter:
    return RateLimiter(1_000, time_provider=lambda: 0.0, sleeper=lambda _: None)


def _make_client(transport: httpx.BaseTransport, max_retries: int = 2) -> HttpClient:
    settings = Settings(max_retries=max_retries)
    return HttpClient(settings=settings, transport=transport, rate_limiter=_instant_rate_limiter())


class _SequenceTransport(httpx.BaseTransport):
    """Devuelve respuestas de una secuencia predefinida."""

    def __init__(self, responses: list[httpx.Response]) -> None:
        self._responses = list(responses)
        self._calls = 0

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        response = self._responses[min(self._calls, len(self._responses) - 1)]
        self._calls += 1
        return response

    @property
    def calls(self) -> int:
        return self._calls


def _make_response(status: int) -> httpx.Response:
    return httpx.Response(status_code=status, text="")


def test_no_retry_on_success() -> None:
    transport = _SequenceTransport([_make_response(200)])
    client = _make_client(transport, max_retries=2)
    response = client.get("http://example.com")
    assert response.status_code == 200
    assert transport.calls == 1


def test_retries_on_503() -> None:
    transport = _SequenceTransport([
        _make_response(503),
        _make_response(503),
        _make_response(200),
    ])
    client = _make_client(transport, max_retries=2)
    slept: list[float] = []

    import semantic_layer_fvl.extractors.http_client as mod
    original_sleep = mod.time.sleep
    mod.time.sleep = slept.append  # type: ignore[method-assign]
    try:
        response = client.get("http://example.com")
    finally:
        mod.time.sleep = original_sleep

    assert response.status_code == 200
    assert transport.calls == 3
    assert len(slept) == 2
    assert slept[0] == 1.0
    assert slept[1] == 2.0


def test_stops_after_max_retries() -> None:
    transport = _SequenceTransport([_make_response(503)] * 5)
    client = _make_client(transport, max_retries=2)

    import semantic_layer_fvl.extractors.http_client as mod
    mod_sleep = mod.time.sleep
    mod.time.sleep = lambda _: None  # type: ignore[method-assign]
    try:
        response = client.get("http://example.com")
    finally:
        mod.time.sleep = mod_sleep

    assert response.status_code == 503
    assert transport.calls == 3


def test_no_retry_on_client_error() -> None:
    transport = _SequenceTransport([_make_response(404)])
    client = _make_client(transport, max_retries=2)
    response = client.get("http://example.com")
    assert response.status_code == 404
    assert transport.calls == 1


def test_retry_after_header_respected() -> None:
    r = httpx.Response(status_code=429, headers={"Retry-After": "5"}, text="")
    transport = _SequenceTransport([r, _make_response(200)])
    client = _make_client(transport, max_retries=1)

    slept: list[float] = []
    import semantic_layer_fvl.extractors.http_client as mod
    mod_sleep = mod.time.sleep
    mod.time.sleep = slept.append  # type: ignore[method-assign]
    try:
        response = client.get("http://example.com")
    finally:
        mod.time.sleep = mod_sleep

    assert response.status_code == 200
    assert slept == [5.0]


def test_backoff_seconds_no_header() -> None:
    from semantic_layer_fvl.extractors.http_client import HttpClient as C
    assert C._backoff_seconds(None, 0) == 1.0
    assert C._backoff_seconds(None, 1) == 2.0
    assert C._backoff_seconds(None, 2) == 4.0
