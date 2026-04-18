from __future__ import annotations

import re


class TextChunker:
    """Split text into overlapping chunks for more precise semantic search.

    Each chunk preserves paragraph boundaries where possible and includes
    metadata about its position within the original document.
    """

    def __init__(
        self,
        max_chunk_size: int = 500,
        chunk_overlap: int = 50,
        min_chunk_size: int = 100,
    ) -> None:
        self.max_chunk_size = max_chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def chunk(self, text: str) -> list[str]:
        """Split text into overlapping chunks respecting paragraph boundaries."""
        if not text or not text.strip():
            return []

        paragraphs = self._split_paragraphs(text)

        if not paragraphs:
            return []

        # If entire text fits in one chunk, return as-is
        full_text = "\n\n".join(paragraphs)
        if len(full_text) <= self.max_chunk_size:
            return [full_text]

        return self._merge_paragraphs_into_chunks(paragraphs)

    def _split_paragraphs(self, text: str) -> list[str]:
        """Split text into clean paragraphs."""
        raw_paragraphs = re.split(r"\n{2,}", text.strip())
        return [p.strip() for p in raw_paragraphs if p.strip()]

    def _merge_paragraphs_into_chunks(self, paragraphs: list[str]) -> list[str]:
        """Merge paragraphs into chunks of max_chunk_size with overlap."""
        chunks: list[str] = []
        current_parts: list[str] = []
        current_length = 0

        for paragraph in paragraphs:
            paragraph_length = len(paragraph)

            # If a single paragraph exceeds max size, split it by sentences
            if paragraph_length > self.max_chunk_size:
                # Flush current buffer first
                if current_parts:
                    chunks.append("\n\n".join(current_parts))
                    current_parts = self._get_overlap_parts(current_parts)
                    current_length = sum(len(p) for p in current_parts)

                sentence_chunks = self._split_long_paragraph(paragraph)
                chunks.extend(sentence_chunks)
                current_parts = []
                current_length = 0
                continue

            # Adding this paragraph would exceed limit -> flush
            new_length = current_length + paragraph_length + (2 if current_parts else 0)
            if new_length > self.max_chunk_size and current_parts:
                chunks.append("\n\n".join(current_parts))
                current_parts = self._get_overlap_parts(current_parts)
                current_length = sum(len(p) for p in current_parts)

            current_parts.append(paragraph)
            current_length += paragraph_length + (2 if len(current_parts) > 1 else 0)

        # Flush remaining
        if current_parts:
            candidate = "\n\n".join(current_parts)
            # If too small and we have a previous chunk, merge with it
            if len(candidate) < self.min_chunk_size and chunks:
                last = chunks.pop()
                chunks.append(f"{last}\n\n{candidate}")
            else:
                chunks.append(candidate)

        return chunks

    def _get_overlap_parts(self, parts: list[str]) -> list[str]:
        """Return trailing paragraphs that fit within the overlap window."""
        if self.chunk_overlap <= 0:
            return []

        overlap_parts: list[str] = []
        total = 0
        for part in reversed(parts):
            total += len(part)
            if total > self.chunk_overlap:
                break
            overlap_parts.insert(0, part)
        return overlap_parts

    def _split_long_paragraph(self, paragraph: str) -> list[str]:
        """Split an oversized paragraph by sentence boundaries."""
        sentences = re.split(r"(?<=[.!?])\s+", paragraph)
        chunks: list[str] = []
        current = ""

        for sentence in sentences:
            candidate = f"{current} {sentence}".strip() if current else sentence
            if len(candidate) > self.max_chunk_size and current:
                chunks.append(current)
                current = sentence
            else:
                current = candidate

        if current:
            chunks.append(current)

        return chunks
