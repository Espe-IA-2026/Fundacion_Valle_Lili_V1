from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import httpx


@dataclass(slots=True)
class RobotsFetchResult:
    url: str
    status_code: int
    text: str | None


@dataclass(slots=True)
class RobotsDecision:
    url: str
    robots_url: str
    allowed: bool
    reason: str


class RobotsPolicy:
    """Resolves and caches robots.txt rules per host."""

    def __init__(
        self,
        user_agent: str,
        *,
        fetcher: Callable[[str], RobotsFetchResult] | None = None,
    ) -> None:
        self.user_agent = user_agent
        self._fetcher = fetcher or self._default_fetcher
        self._parsers: dict[str, RobotFileParser | None] = {}
        self._reasons: dict[str, str] = {}

    def evaluate(self, url: str) -> RobotsDecision:
        robots_url = self.resolve_robots_url(url)
        parser = self._get_parser(robots_url)
        if parser is None:
            reason = self._reasons.get(robots_url, "robots_unavailable")
            return RobotsDecision(url=url, robots_url=robots_url, allowed=False, reason=reason)

        allowed = parser.can_fetch(self.user_agent, url)
        reason = "allowed" if allowed else "blocked_by_robots"
        return RobotsDecision(url=url, robots_url=robots_url, allowed=allowed, reason=reason)

    def is_allowed(self, url: str) -> bool:
        return self.evaluate(url).allowed

    @staticmethod
    def resolve_robots_url(url: str) -> str:
        parts = urlsplit(url)
        return urlunsplit((parts.scheme, parts.netloc, "/robots.txt", "", ""))

    def _get_parser(self, robots_url: str) -> RobotFileParser | None:
        if robots_url in self._parsers:
            return self._parsers[robots_url]

        result = self._fetcher(robots_url)
        if 400 <= result.status_code < 500 and result.status_code != 429:
            parser = RobotFileParser()
            parser.parse([])
            self._parsers[robots_url] = parser
            self._reasons[robots_url] = f"robots_unavailable_allow_all:{result.status_code}"
            return parser

        if result.status_code >= 400 or result.text is None:
            self._parsers[robots_url] = None
            self._reasons[robots_url] = f"robots_fetch_failed:{result.status_code}"
            return None

        parser = RobotFileParser()
        parser.set_url(robots_url)
        parser.parse(result.text.splitlines())
        self._parsers[robots_url] = parser
        self._reasons[robots_url] = "robots_loaded"
        return parser

    def _default_fetcher(self, robots_url: str) -> RobotsFetchResult:
        with httpx.Client(
            follow_redirects=True,
            timeout=30.0,
            headers={"User-Agent": self.user_agent},
        ) as client:
            response = client.get(robots_url)
            return RobotsFetchResult(
                url=str(response.url),
                status_code=response.status_code,
                text=response.text if response.text else None,
            )
