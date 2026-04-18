from __future__ import annotations

from semantic_layer_fvl.extractors.robots import RobotsFetchResult, RobotsPolicy


def test_robots_policy_blocks_disallowed_paths() -> None:
    def fetcher(robots_url: str) -> RobotsFetchResult:
        return RobotsFetchResult(
            url=robots_url,
            status_code=200,
            text="User-agent: *\nDisallow: /privado\n",
        )

    policy = RobotsPolicy("semantic-layer-fvl-test", fetcher=fetcher)

    assert policy.is_allowed("https://valledellili.org/publico")
    assert not policy.is_allowed("https://valledellili.org/privado")


def test_missing_robots_defaults_to_allow_all() -> None:
    def fetcher(robots_url: str) -> RobotsFetchResult:
        return RobotsFetchResult(url=robots_url, status_code=404, text=None)

    policy = RobotsPolicy("semantic-layer-fvl-test", fetcher=fetcher)

    decision = policy.evaluate("https://valledellili.org/cualquier-ruta")

    assert decision.allowed is True
    assert decision.reason == "allowed"


def test_forbidden_robots_is_treated_as_unavailable_and_allows_crawl() -> None:
    def fetcher(robots_url: str) -> RobotsFetchResult:
        return RobotsFetchResult(url=robots_url, status_code=403, text=None)

    policy = RobotsPolicy("semantic-layer-fvl-test", fetcher=fetcher)

    decision = policy.evaluate("https://valledellili.org/quienes-somos")

    assert decision.allowed is True
    assert decision.reason == "allowed"
