"""Generador de URLs de feed RSS de Google News para búsquedas relacionadas con FVL."""

from __future__ import annotations

from urllib.parse import quote_plus


class GoogleNewsFeedBuilder:
    """Construye URLs de feeds RSS de Google News para búsquedas institucionales.

    Google News expone un endpoint RSS no oficial que permite buscar noticias por
    palabra clave. Este builder genera las URLs correctas con los parámetros de
    idioma y región para Colombia.

    Attributes:
        queries: Lista de términos de búsqueda para los cuales generar feeds RSS.
    """

    _BASE_URL = "https://news.google.com/rss/search"
    _LOCALE_PARAMS = "hl=es-419&gl=CO&ceid=CO:es"

    def __init__(self, queries: list[str] | None = None) -> None:
        """Inicializa el generador con las queries configuradas.

        Args:
            queries: Lista de términos de búsqueda. Si es ``None`` usa :data:`FVL_SEARCH_QUERIES`.
        """
        if queries is None:
            from semantic_layer_fvl.news_feeds import FVL_SEARCH_QUERIES
            queries = FVL_SEARCH_QUERIES
        self.queries = queries

    def feed_urls(self) -> list[str]:
        """Devuelve las URLs de feeds RSS de Google News para las queries configuradas.

        Returns:
            Lista de URLs de feeds RSS listos para ser procesados por ``NewsFeedExtractor``.
        """
        return [self._build_url(query) for query in self.queries]

    def _build_url(self, query: str) -> str:
        """Construye la URL del feed RSS de Google News para un término de búsqueda.

        Args:
            query: Término de búsqueda a codificar en la URL.

        Returns:
            URL completa del feed RSS de Google News.
        """
        encoded = quote_plus(query)
        return f"{self._BASE_URL}?q={encoded}&{self._LOCALE_PARAMS}"
