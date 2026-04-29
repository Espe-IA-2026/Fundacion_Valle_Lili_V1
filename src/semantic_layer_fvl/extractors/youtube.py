"""Extractor de feeds Atom públicos de YouTube hacia registros ``RawPage``."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from semantic_layer_fvl.config import Settings, get_settings
from semantic_layer_fvl.extractors.http_client import HttpClient
from semantic_layer_fvl.schemas import ExtractionMetadata, RawPage

ATOM_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "media": "http://search.yahoo.com/mrss/",
}


class YouTubeFeedExtractor:
    """Parsea feeds Atom públicos de YouTube y los convierte en registros ``RawPage``."""

    def __init__(
        self,
        client: HttpClient | None = None,
        *,
        settings: Settings | None = None,
        source_name: str = "YouTube",
    ) -> None:
        """Inicializa el extractor de feeds de YouTube.

        Args:
            client: Cliente HTTP a utilizar. Si es ``None`` se crea uno con ``settings``.
            settings: Configuración del proyecto. Si es ``None`` se obtiene la instancia global.
            source_name: Nombre de la fuente para los metadatos de extracción.
        """
        self.settings = settings or get_settings()
        self.client = client or HttpClient(self.settings)
        self.source_name = source_name

    def fetch_feed(self, feed_url: str) -> list[RawPage]:
        """Descarga y parsea el feed Atom de YouTube, retornando una lista de ``RawPage``.

        Args:
            feed_url: URL del feed Atom público del canal de YouTube.

        Returns:
            Lista de ``RawPage`` con hasta ``youtube_search_limit`` entradas.
        """
        response = self.client.get(feed_url)
        response.raise_for_status()

        root = ET.fromstring(response.text)
        entries = root.findall("atom:entry", ATOM_NS)
        pages: list[RawPage] = []

        for entry in entries[: self.settings.youtube_search_limit]:
            title = self._get_text(entry, "atom:title")
            link = self._get_link(entry)
            description = self._get_text(entry, "media:group/media:description")
            author = self._get_text(entry, "atom:author/atom:name")
            published = self._get_text(entry, "atom:published")

            metadata = ExtractionMetadata(
                source_url=link,
                source_name=self.source_name,
                extractor_name="youtube_feed",
                http_status=response.status_code,
                content_type=response.headers.get("content-type"),
            )
            parts = [
                title,
                description,
                f"Autor: {author}" if author else None,
                published,
            ]
            text_content = "\n\n".join(part for part in parts if part)
            pages.append(
                RawPage(
                    url=link,
                    title=title,
                    text_content=text_content,
                    metadata=metadata,
                )
            )

        return pages

    @staticmethod
    def _get_text(element: ET.Element, path: str) -> str | None:
        """Busca un elemento hijo por ruta XPath y devuelve su texto limpio, o ``None``."""
        found = element.find(path, ATOM_NS)
        if found is None or found.text is None:
            return None
        text = found.text.strip()
        return text or None

    @staticmethod
    def _get_link(entry: ET.Element) -> str:
        """Extrae el atributo ``href`` del primer enlace Atom de una entrada.

        Raises:
            ValueError: Si la entrada no contiene ningún enlace.
        """
        for link in entry.findall("atom:link", ATOM_NS):
            href = link.attrib.get("href")
            if href:
                return href
        raise ValueError("YouTube feed entry does not include a link.")
