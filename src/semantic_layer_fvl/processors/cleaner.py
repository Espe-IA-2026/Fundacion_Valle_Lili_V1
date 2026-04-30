"""Normalización de texto extraído y eliminación de ruido de navegación."""

from __future__ import annotations

import re


class TextCleaner:
    """Normaliza texto extraído y elimina ruido de navegación común."""

    def __init__(
        self,
        *,
        min_line_length: int = 2,
        extra_noise: frozenset[str] | set[str] | None = None,
    ) -> None:
        """Inicializa el limpiador de texto.

        Args:
            min_line_length: Longitud mínima de caracteres que debe tener una línea
                para no ser descartada como ruido.
            extra_noise: Conjunto adicional de líneas de ruido específicas de la fuente.
                Se fusiona con el conjunto base predeterminado. Puede pasarse uno de los
                presets definidos en :mod:`semantic_layer_fvl.processors.noise_presets`.
        """
        self.min_line_length = min_line_length
        base_noise: set[str] = {
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
        }
        self._noise_lines = base_noise | (extra_noise or set())

    def clean(self, text: str | None) -> str:
        """Limpia y normaliza el texto eliminando duplicados y líneas de ruido.

        Args:
            text: Texto crudo a procesar. Si es ``None`` o vacío, devuelve ``""``.

        Returns:
            Texto limpio con líneas únicas, sin ruido y con espacios normalizados.
        """
        if not text:
            return ""

        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        lines = [self._normalize_line(line) for line in normalized.split("\n")]

        cleaned_lines: list[str] = []
        seen_lines: set[str] = set()
        for line in lines:
            if not line:
                if cleaned_lines and cleaned_lines[-1] != "":
                    cleaned_lines.append("")
                continue

            if self._is_noise(line):
                continue

            line_key = line.casefold()
            if line_key in seen_lines:
                continue
            seen_lines.add(line_key)
            cleaned_lines.append(line)

        while cleaned_lines and cleaned_lines[-1] == "":
            cleaned_lines.pop()

        return "\n".join(cleaned_lines)

    @staticmethod
    def split_paragraphs(text: str) -> list[str]:
        """Divide el texto en párrafos no vacíos separados por líneas en blanco."""
        return [chunk.strip() for chunk in text.split("\n\n") if chunk.strip()]

    def _is_noise(self, line: str) -> bool:
        """Devuelve ``True`` si la línea es considerada ruido de navegación."""
        lowered = line.casefold()
        if lowered in self._noise_lines:
            return True
        return len(line) < self.min_line_length

    @staticmethod
    def _normalize_line(line: str) -> str:
        """Colapsa espacios internos y corrige puntuación pegada en una línea."""
        compact = re.sub(r"\s+", " ", line).strip()
        compact = compact.replace(" ,", ",").replace(" .", ".")
        return compact
