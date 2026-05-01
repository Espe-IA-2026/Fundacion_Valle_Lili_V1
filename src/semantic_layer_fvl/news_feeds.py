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
        requires_relevance_filter: Si es ``True``, solo se procesan items cuyo
            título o cuerpo contenga alguna keyword de :data:`FVL_RELEVANCE_KEYWORDS`.
            Útil para feeds genéricos (todos los temas de salud) donde queremos
            quedarnos solo con noticias sobre la FVL. Para feeds que ya están
            pre-filtrados (Google News con query "Fundación Valle del Lili"),
            ponerlo en ``False`` para procesar todo.
    """

    url: str
    name: str
    extra_noise: frozenset[str] = field(default_factory=frozenset)
    requires_relevance_filter: bool = True


FVL_RELEVANCE_KEYWORDS: frozenset[str] = frozenset(
    {
        "fundación valle del lili",
        "fundacion valle del lili",
        "valle del lili",
        "hospital valle del lili",
        "fundación valle lili",
        "fvl",
    }
)


def is_fvl_relevant(*texts: str | None) -> bool:
    """Determina si alguno de los textos contiene una keyword de la FVL.

    Args:
        *texts: Cadenas a inspeccionar (título, cuerpo, etc.). ``None`` se ignora.

    Returns:
        ``True`` si al menos una keyword de :data:`FVL_RELEVANCE_KEYWORDS` aparece
        en el texto combinado (case-insensitive y sin acentos).
    """
    combined = " ".join(t for t in texts if t).casefold()
    if not combined:
        return False
    return any(kw in combined for kw in FVL_RELEVANCE_KEYWORDS)


CURATED_NEWS_FEEDS: list[NewsFeedConfig] = [
    NewsFeedConfig(
        url="https://www.eltiempo.com/rss/salud_seccion-salud.xml",
        name="El Tiempo — Salud",
        requires_relevance_filter=True,
    ),
    NewsFeedConfig(
        url="https://www.elpais.com.co/feed/",
        name="El País Cali",
        requires_relevance_filter=True,
    ),
    NewsFeedConfig(
        url="https://www.semana.com/rss/feed/",
        name="Semana",
        requires_relevance_filter=True,
    ),
    NewsFeedConfig(
        url="https://www.elespectador.com/arc/outboundfeeds/rss/section/salud/?outputType=xml",
        name="El Espectador — Salud",
        requires_relevance_filter=True,
    ),
    NewsFeedConfig(
        url="https://caracol.com.co/feed/",
        name="Caracol Radio",
        requires_relevance_filter=True,
    ),
    NewsFeedConfig(
        url="https://www.bluradio.com/feed",
        name="Blu Radio",
        requires_relevance_filter=True,
    ),
    NewsFeedConfig(
        url="https://www.rcnradio.com/rss/colombia.xml",
        name="RCN Radio",
        requires_relevance_filter=True,
    ),
]

FVL_SEARCH_QUERIES: list[str] = [
    "Fundación Valle del Lili",
    "Hospital Valle del Lili",
    "FVL Cali trasplantes",
]
