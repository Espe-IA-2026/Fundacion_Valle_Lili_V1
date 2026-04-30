"""Feeds de noticias curados y queries de búsqueda relacionados con la Fundación Valle del Lili."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class NewsFeedConfig:
    """Configuración de un feed de noticias curado.

    Attributes:
        url: URL del feed RSS o Atom.
        name: Nombre legible del medio o fuente.
        extra_noise: Frases adicionales de ruido a filtrar específicas de este feed.
    """

    url: str
    name: str
    extra_noise: frozenset[str] = field(default_factory=frozenset)


CURATED_NEWS_FEEDS: list[NewsFeedConfig] = [
    NewsFeedConfig(
        url="https://www.eltiempo.com/rss/salud.xml",
        name="El Tiempo — Salud",
    ),
    NewsFeedConfig(
        url="https://www.elpais.com.co/rss.xml",
        name="El País Cali",
    ),
    NewsFeedConfig(
        url="https://www.semana.com/rss/salud.xml",
        name="Semana — Salud",
    ),
    NewsFeedConfig(
        url="https://www.elespectador.com/rss/salud.xml",
        name="El Espectador — Salud",
    ),
    NewsFeedConfig(
        url="https://www.caracol.com.co/rss/categoria/salud.xml",
        name="Caracol — Salud",
    ),
    NewsFeedConfig(
        url="https://www.bluradio.com/rss.xml",
        name="Blu Radio",
    ),
    NewsFeedConfig(
        url="https://www.rcnradio.com/rss.xml",
        name="RCN Radio",
    ),
]

FVL_SEARCH_QUERIES: list[str] = [
    "Fundación Valle del Lili",
    "Hospital Valle del Lili",
    "FVL Cali trasplantes",
]
