"""Extractor enriquecido de videos de YouTube con metadatos completos y transcripciones."""

from __future__ import annotations

import json
import logging
import re

import httpx

from semantic_layer_fvl.config import Settings, get_settings
from semantic_layer_fvl.schemas import ExtractionMetadata, RawPage

logger = logging.getLogger(__name__)

_DEFAULT_TRANSCRIPT_LANGS: tuple[str, ...] = ("es", "es-419", "es-CO", "en")
_SEARCH_PREFIX = "ytsearch"

_PROMO_PATTERN = re.compile(
    r"(suscrib|follow|síguenos|siguenos|instagram|facebook|twitter|tiktok"
    r"|http[s]?://|www\.|bit\.ly|youtu\.be)",
    re.IGNORECASE,
)


class YouTubeRichExtractor:
    """Extrae metadatos completos y transcripciones de videos de YouTube usando yt-dlp.

    A diferencia de :class:`YouTubeFeedExtractor` (que parsea feeds Atom públicos),
    este extractor usa ``yt-dlp`` para obtener descripción completa, duración, tags
    y subtítulos automáticos. También permite buscar videos por palabra clave.

    Attributes:
        settings: Configuración del proyecto.
        source_name: Nombre de la fuente para los metadatos de extracción.
        transcript_langs: Orden de preferencia de idiomas para la transcripción.
    """

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        source_name: str = "YouTube",
        transcript_langs: tuple[str, ...] = _DEFAULT_TRANSCRIPT_LANGS,
    ) -> None:
        """Inicializa el extractor de YouTube enriquecido.

        Args:
            settings: Configuración del proyecto. Si es ``None`` se obtiene la instancia global.
            source_name: Nombre de la fuente para los metadatos de extracción.
            transcript_langs: Idiomas a intentar en orden de preferencia al extraer transcripciones.
        """
        self.settings = settings or get_settings()
        self.source_name = source_name
        self.transcript_langs = transcript_langs

    def fetch_video(self, video_url: str) -> RawPage:
        """Descarga los metadatos completos y la transcripción de un video de YouTube.

        Args:
            video_url: URL del video (``youtube.com/watch?v=...`` o ``youtu.be/...``).

        Returns:
            ``RawPage`` con título, descripción limpia y transcripción en ``text_content``.

        Raises:
            ImportError: Si ``yt-dlp`` no está instalado en el entorno.
        """
        import yt_dlp  # noqa: PLC0415

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)

        return self._build_raw_page(info or {}, video_url)

    def search_videos(self, query: str, limit: int | None = None) -> list[str]:
        """Busca videos en YouTube por palabra clave y devuelve sus URLs.

        Args:
            query: Término de búsqueda (p.ej. ``"Fundación Valle del Lili"``).
            limit: Número máximo de resultados. Si es ``None`` usa ``youtube_search_limit``.

        Returns:
            Lista de URLs ``youtube.com/watch?v=...`` de los videos encontrados.

        Raises:
            ImportError: Si ``yt-dlp`` no está instalado en el entorno.
        """
        import yt_dlp  # noqa: PLC0415

        actual_limit = min(limit or self.settings.youtube_search_limit, self.settings.youtube_search_limit)
        search_url = f"{_SEARCH_PREFIX}{actual_limit}:{query}"

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "extract_flat": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(search_url, download=False) or {}

        entries = result.get("entries") or []
        urls: list[str] = []
        for entry in entries:
            if entry and entry.get("id"):
                urls.append(f"https://www.youtube.com/watch?v={entry['id']}")
        return urls

    def _build_raw_page(self, info: dict, original_url: str) -> RawPage:
        """Construye un ``RawPage`` a partir del diccionario de metadatos de yt-dlp."""
        title = info.get("title") or "Sin título"
        channel = info.get("channel") or info.get("uploader") or ""
        description = info.get("description") or ""
        upload_date = info.get("upload_date") or ""
        duration = int(info.get("duration") or 0)
        video_id = info.get("id") or ""
        webpage_url = info.get("webpage_url") or original_url

        upload_date_fmt = self._format_date(upload_date)
        duration_fmt = self._format_duration(duration) if duration else "Desconocida"
        clean_desc = self._clean_description(description)
        transcript = self._extract_transcript(info)

        parts = [
            f"# {title}",
            "",
            f"**Canal:** {channel}",
            f"**Publicado:** {upload_date_fmt}",
            f"**Duración:** {duration_fmt}",
            "",
            "## Descripción",
            clean_desc or "_Sin descripción disponible._",
            "",
            "## Transcripción",
            transcript or "_Transcripción no disponible._",
        ]
        text_content = "\n".join(parts)

        metadata = ExtractionMetadata(
            source_url=webpage_url,
            source_name=self.source_name,
            extractor_name="youtube_rich",
            checksum=video_id,
        )
        return RawPage(
            url=webpage_url,
            title=title,
            text_content=text_content,
            metadata=metadata,
            extra_metadata={
                "video_id": video_id,
                "channel": channel,
                "duration_seconds": str(duration),
                "upload_date": upload_date_fmt,
                "source_type": "youtube_rich",
            },
        )

    def _extract_transcript(self, info: dict) -> str | None:
        """Extrae el texto de la transcripción del video, priorizando subtítulos manuales."""
        subtitles: dict = info.get("subtitles") or {}
        auto_captions: dict = info.get("automatic_captions") or {}

        for lang in self.transcript_langs:
            captions = subtitles.get(lang) or auto_captions.get(lang)
            if captions:
                text = self._fetch_caption_text(captions)
                if text:
                    return text
        return None

    @staticmethod
    def _fetch_caption_text(caption_list: list[dict]) -> str | None:
        """Descarga y convierte a texto plano la primera fuente de subtítulos disponible."""
        for cap in caption_list:
            url = cap.get("url")
            ext = str(cap.get("ext") or "")
            if not url:
                continue
            try:
                response = httpx.get(url, timeout=10, follow_redirects=True)
                response.raise_for_status()
                if "json3" in ext or "json3" in url:
                    return YouTubeRichExtractor._parse_json3(response.text)
                return YouTubeRichExtractor._parse_vtt(response.text)
            except Exception:
                continue
        return None

    @staticmethod
    def _parse_vtt(vtt_text: str) -> str:
        """Extrae texto puro de un archivo VTT eliminando timestamps y etiquetas HTML."""
        lines: list[str] = []
        for line in vtt_text.splitlines():
            if re.match(r"^\d{2}:\d{2}", line) or line.startswith("WEBVTT") or not line.strip():
                continue
            clean = re.sub(r"<[^>]+>", "", line).strip()
            if clean:
                lines.append(clean)
        result: list[str] = []
        for line in lines:
            if not result or result[-1] != line:
                result.append(line)
        return " ".join(result)

    @staticmethod
    def _parse_json3(json_text: str) -> str:
        """Extrae texto de subtítulos en formato json3 de YouTube."""
        try:
            data = json.loads(json_text)
            texts: list[str] = []
            for event in data.get("events") or []:
                for seg in event.get("segs") or []:
                    text = seg.get("utf8", "")
                    if text and text.strip() and text != "\n":
                        texts.append(text.strip())
            return " ".join(texts)
        except Exception:
            return ""

    @staticmethod
    def _clean_description(description: str) -> str:
        """Elimina URLs y líneas promocionales de la descripción del video."""
        if not description:
            return ""
        lines: list[str] = []
        for line in description.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if _PROMO_PATTERN.search(stripped):
                continue
            lines.append(stripped)
        return "\n".join(lines)

    @staticmethod
    def _format_date(upload_date: str) -> str:
        """Convierte la fecha YYYYMMDD de yt-dlp al formato ISO ``YYYY-MM-DD``."""
        if len(upload_date) == 8:
            return f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}"
        return upload_date or "Desconocida"

    @staticmethod
    def _format_duration(seconds: int) -> str:
        """Formatea segundos como ``H:MM:SS`` o ``M:SS``."""
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        if h:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"
