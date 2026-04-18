from __future__ import annotations

import re


class TextCleaner:
    """Normalizes extracted text and removes common navigation noise."""

    def __init__(self, *, min_line_length: int = 2) -> None:
        self.min_line_length = min_line_length
        self._noise_lines = {
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

    def clean(self, text: str | None) -> str:
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
        return [chunk.strip() for chunk in text.split("\n\n") if chunk.strip()]

    def _is_noise(self, line: str) -> bool:
        lowered = line.casefold()
        if lowered in self._noise_lines:
            return True
        return len(line) < self.min_line_length

    @staticmethod
    def _normalize_line(line: str) -> str:
        compact = re.sub(r"\s+", " ", line).strip()
        compact = compact.replace(" ,", ",").replace(" .", ".")
        return compact
