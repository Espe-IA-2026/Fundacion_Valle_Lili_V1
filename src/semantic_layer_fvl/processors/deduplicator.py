"""Deduplicación de contenido entre fuentes mediante URL canónica y checksum SHA-256."""

from __future__ import annotations

import hashlib
import re
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse


class ContentDeduplicator:
    """Filtra documentos duplicados entre fuentes usando URL canónica y checksum de contenido.

    Mantiene estado interno de URLs y checksums vistos durante una corrida del pipeline.
    Cada instancia representa un contexto de deduplicación independiente.

    Attributes:
        _seen_urls: Conjunto de URLs canónicas ya procesadas.
        _seen_checksums: Conjunto de checksums SHA-256 de contenidos ya procesados.
    """

    _TRACKING_PARAMS: frozenset[str] = frozenset({
        "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term",
        "fbclid", "gclid", "msclkid", "ref", "source",
    })

    def __init__(self) -> None:
        """Inicializa el deduplicador con conjuntos vacíos de URLs y checksums."""
        self._seen_urls: set[str] = set()
        self._seen_checksums: set[str] = set()

    def is_duplicate(self, url: str, text_content: str | None) -> bool:
        """Verifica si la URL o el contenido ya fueron procesados en esta instancia.

        Si no es duplicado, registra la URL y el checksum del contenido para
        detecciones futuras.

        Args:
            url: URL del recurso a verificar.
            text_content: Texto del contenido; si es ``None`` solo se compara por URL.

        Returns:
            ``True`` si la URL canónica o el checksum del contenido ya fueron vistos.
        """
        canonical = self.canonical_url(url)

        if canonical in self._seen_urls:
            return True

        if text_content:
            checksum = self.content_checksum(text_content)
            if checksum in self._seen_checksums:
                return True
            self._seen_checksums.add(checksum)

        self._seen_urls.add(canonical)
        return False

    @classmethod
    def canonical_url(cls, url: str) -> str:
        """Normaliza una URL eliminando parámetros de tracking y variantes de YouTube.

        Convierte ``youtu.be/ID`` a ``youtube.com/watch?v=ID`` y elimina parámetros
        de seguimiento como ``utm_*``, ``fbclid``, etc.

        Args:
            url: URL a normalizar.

        Returns:
            URL canónica en minúsculas, sin fragmento y sin parámetros de tracking.
        """
        parsed = urlparse(url.strip())

        if parsed.netloc in ("youtu.be",):
            video_id = parsed.path.lstrip("/")
            return f"https://www.youtube.com/watch?v={video_id}"

        if parsed.query:
            qs = parse_qs(parsed.query, keep_blank_values=True)
            filtered = {k: v for k, v in qs.items() if k.lower() not in cls._TRACKING_PARAMS}
            new_query = urlencode(filtered, doseq=True)
        else:
            new_query = ""

        return urlunparse((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path,
            parsed.params,
            new_query,
            "",
        ))

    @staticmethod
    def content_checksum(text: str) -> str:
        """Calcula el SHA-256 del texto normalizado (minúsculas + espacios colapsados).

        Args:
            text: Texto a procesar.

        Returns:
            Cadena hexadecimal de 64 caracteres con el hash SHA-256.
        """
        normalized = re.sub(r"\s+", " ", text.casefold()).strip()
        return hashlib.sha256(normalized.encode()).hexdigest()
