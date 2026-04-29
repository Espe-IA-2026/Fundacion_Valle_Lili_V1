"""Cliente HTTP compartido con limitación de tasa para el pipeline de extracción."""

from __future__ import annotations

import time
from collections.abc import Callable

import httpx

from semantic_layer_fvl.config import Settings, get_settings


class RateLimiter:
    """Limitador de tasa de intervalo fijo entre peticiones HTTP consecutivas."""

    def __init__(
        self,
        requests_per_second: float,
        *,
        time_provider: Callable[[], float] | None = None,
        sleeper: Callable[[float], None] | None = None,
    ) -> None:
        """Inicializa el limitador de tasa.

        Args:
            requests_per_second: Número máximo de peticiones permitidas por segundo.
            time_provider: Función que devuelve el tiempo monotónico actual (inyectable para pruebas).
            sleeper: Función que pausa la ejecución el número de segundos indicado (inyectable para pruebas).
        """
        self._minimum_interval = 1 / requests_per_second
        self._time_provider = time_provider or time.monotonic
        self._sleeper = sleeper or time.sleep
        self._last_request_at: float | None = None

    @property
    def minimum_interval(self) -> float:
        """Intervalo mínimo en segundos entre peticiones consecutivas."""
        return self._minimum_interval

    def wait(self) -> None:
        """Bloquea la ejecución el tiempo necesario para respetar el intervalo configurado."""
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
    """Cliente HTTP con cabeceras y configuración predeterminada para el pipeline de extracción."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        transport: httpx.BaseTransport | None = None,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        """Inicializa el cliente HTTP con configuración inyectable.

        Args:
            settings: Configuración del proyecto. Si es ``None`` se obtiene la instancia global.
            transport: Transporte httpx personalizado (útil para pruebas con mocks).
            rate_limiter: Limitador de tasa a utilizar. Si es ``None`` se crea uno con la
                configuración de ``settings``.
        """
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
        """Realiza una petición GET respetando el intervalo de tasa configurado.

        Args:
            url: URL absoluta del recurso a obtener.

        Returns:
            Objeto ``httpx.Response`` con la respuesta del servidor.
        """
        self.rate_limiter.wait()
        return self._client.get(url)

    def _build_default_headers(self) -> dict[str, str]:
        """Construye el diccionario de cabeceras HTTP predeterminadas."""
        return {
            "User-Agent": self.settings.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": self.settings.accept_language,
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Upgrade-Insecure-Requests": "1",
        }

    def close(self) -> None:
        """Cierra el cliente HTTP subyacente y libera recursos."""
        self._client.close()

    def __enter__(self) -> HttpClient:
        """Permite usar el cliente como gestor de contexto."""
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        """Cierra el cliente al salir del bloque ``with``."""
        self.close()
