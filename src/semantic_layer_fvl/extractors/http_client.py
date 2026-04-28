from __future__ import annotations

import time
from collections.abc import Callable

import httpx

from semantic_layer_fvl.config import Settings, get_settings


class RateLimiter:
    """Simple fixed-interval rate limiter."""

    def __init__(
        self,
        requests_per_second: float,
        *,
        time_provider: Callable[[], float] | None = None,
        sleeper: Callable[[float], None] | None = None,
    ) -> None:
        self._minimum_interval = 1 / requests_per_second
        self._time_provider = time_provider or time.monotonic
        self._sleeper = sleeper or time.sleep
        self._last_request_at: float | None = None

    @property
    def minimum_interval(self) -> float:
        return self._minimum_interval

    def wait(self) -> None:
        now = self._time_provider()
        if self._last_request_at is None:
            self._last_request_at = now
            return

        elapsed = now - self._last_request_at
        remaining = self._minimum_interval - elapsed
        if remaining > 0:
            self._sleeper(remaining)
            now = self._time_provider()

        self._last_request_at = now


class HttpClient:
    """HTTP client with shared defaults for the extraction pipeline."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        transport: httpx.BaseTransport | None = None,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.rate_limiter = rate_limiter or RateLimiter(
            self.settings.requests_per_second
        )
        self._client = httpx.Client(
            follow_redirects=True,
            headers=self._build_default_headers(),
            timeout=self.settings.request_timeout,
            transport=transport,
        )

    def get(self, url: str) -> httpx.Response:
        self.rate_limiter.wait()
        return self._client.get(url)

    def _build_default_headers(self) -> dict[str, str]:
        return {
            "User-Agent": self.settings.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": self.settings.accept_language,
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Upgrade-Insecure-Requests": "1",
        }

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> HttpClient:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()
