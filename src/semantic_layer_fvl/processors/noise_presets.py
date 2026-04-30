"""Conjuntos de líneas de ruido predefinidos para distintas fuentes de extracción.

Cada preset puede pasarse como ``extra_noise`` al constructor de ``TextCleaner``
para adaptar el filtrado a la fuente procesada.
"""

from __future__ import annotations

WEB_FVL_NOISE: frozenset[str] = frozenset({
    "menu",
    "inicio",
    "home",
    "cerrar",
    "abrir",
    "facebook",
    "instagram",
    "linkedin",
    "youtube",
    "twitter",
    "x",
})

NEWS_NOISE: frozenset[str] = frozenset({
    "lee también",
    "leer también",
    "ver más",
    "ver mas",
    "compartir",
    "compartir en",
    "suscríbete",
    "suscribete",
    "newsletter",
    "subscríbete",
    "subscribete",
    "comentarios",
    "deja un comentario",
    "publicidad",
    "relacionados",
    "noticias relacionadas",
    "más noticias",
    "continúa leyendo",
    "continua leyendo",
    "leer más",
    "leer mas",
    "artículo relacionado",
    "publicado por",
    "escrito por",
})

YOUTUBE_NOISE: frozenset[str] = frozenset({
    "suscríbete",
    "suscribete",
    "subscríbete",
    "subscribete",
    "activa la campanita",
    "activa la campana",
    "sígueme en",
    "sigueme en",
    "dale like",
    "siguiente video",
    "video anterior",
    "comentarios",
    "deja tu comentario",
    "link en la descripción",
    "link en la descripcion",
})
