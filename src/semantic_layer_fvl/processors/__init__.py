"""Submódulo de procesadores: limpieza, estructuración, deduplicación y chunking."""

from semantic_layer_fvl.processors.chunker import (
    TextChunker,
)  # Reservado para la versión 2.0, actualmente no se utiliza solo se implementa la logica para este entregable, pero se deja la estructura para futuras implementaciones.
from semantic_layer_fvl.processors.cleaner import TextCleaner
from semantic_layer_fvl.processors.deduplicator import ContentDeduplicator
from semantic_layer_fvl.processors.noise_presets import NEWS_NOISE, WEB_FVL_NOISE, YOUTUBE_NOISE
from semantic_layer_fvl.processors.structurer import SemanticStructurer, slugify

__all__ = [
    "ContentDeduplicator",
    "NEWS_NOISE",
    "SemanticStructurer",
    "TextCleaner",
    "WEB_FVL_NOISE",
    "YOUTUBE_NOISE",
    "slugify",
]
