"""Evaluador de reglas ``robots.txt`` con caché por host para el pipeline de extracción."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import httpx


@dataclass(slots=True)
class RobotsFetchResult:
    """Resultado de la petición al archivo ``robots.txt`` de un host.

    Attributes:
        url: URL final del ``robots.txt`` (tras posibles redirecciones).
        status_code: Código de respuesta HTTP recibido.
        text: Contenido textual del archivo, o ``None`` si no fue obtenido.
    """

    url: str
    status_code: int
    text: str | None


@dataclass(slots=True)
class RobotsDecision:
    """Decisión de acceso a una URL según las reglas del ``robots.txt`` del host.

    Attributes:
        url: URL evaluada.
        robots_url: URL del archivo ``robots.txt`` consultado.
        allowed: ``True`` si el acceso está permitido.
        reason: Razón de la decisión (p.ej. ``"allowed"``, ``"blocked_by_robots"``).
    """

    url: str
    robots_url: str
    allowed: bool
    reason: str


class RobotsPolicy:
    """Evalúa y almacena en caché las reglas de ``robots.txt`` por host."""

    def __init__(
        self,
        user_agent: str,
        *,
        fetcher: Callable[[str], RobotsFetchResult] | None = None,
    ) -> None:
        """Inicializa la política de robots con el agente de usuario dado.

        Args:
            user_agent: Cadena de identificación del crawler para las reglas del ``robots.txt``.
            fetcher: Función que obtiene el ``robots.txt`` de una URL (inyectable para pruebas).
        """
        self.user_agent = user_agent
        self._fetcher = fetcher or self._default_fetcher
        self._parsers: dict[str, RobotFileParser | None] = {}
        self._reasons: dict[str, str] = {}

    def evaluate(self, url: str) -> RobotsDecision:
        """Evalúa si el ``user_agent`` tiene permiso para acceder a la URL.

        Args:
            url: URL absoluta a evaluar.

        Returns:
            ``RobotsDecision`` con el resultado y la razón de la decisión.
        """
        robots_url = self.resolve_robots_url(url)
        parser = self._get_parser(robots_url)
        if parser is None:
            reason = self._reasons.get(robots_url, "robots_unavailable")
            return RobotsDecision(url=url, robots_url=robots_url, allowed=False, reason=reason)

        allowed = parser.can_fetch(self.user_agent, url)
        reason = "allowed" if allowed else "blocked_by_robots"
        return RobotsDecision(url=url, robots_url=robots_url, allowed=allowed, reason=reason)

    def is_allowed(self, url: str) -> bool:
        """Devuelve ``True`` si el acceso a la URL está permitido por el ``robots.txt``."""
        return self.evaluate(url).allowed

    @staticmethod
    def resolve_robots_url(url: str) -> str:
        """Construye la URL canónica del ``robots.txt`` para el host de la URL dada."""
        parts = urlsplit(url)
        return urlunsplit((parts.scheme, parts.netloc, "/robots.txt", "", ""))

    def _get_parser(self, robots_url: str) -> RobotFileParser | None:
        """Obtiene (o crea y almacena en caché) el parser para el ``robots.txt`` del host."""
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
        """Descarga el ``robots.txt`` usando httpx con el ``User-Agent`` del crawler."""
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
