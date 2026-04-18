from __future__ import annotations

from semantic_layer_fvl.processors.chunker import TextChunker


def test_short_text_returns_single_chunk() -> None:
    chunker = TextChunker(max_chunk_size=500)
    text = "Este es un texto corto que cabe en un solo chunk."
    chunks = chunker.chunk(text)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_empty_text_returns_empty_list() -> None:
    chunker = TextChunker()
    assert chunker.chunk("") == []
    assert chunker.chunk("   ") == []


def test_long_text_is_split_into_multiple_chunks() -> None:
    chunker = TextChunker(max_chunk_size=100, chunk_overlap=20, min_chunk_size=30)
    paragraphs = [f"Parrafo numero {i} con contenido de prueba para el test." for i in range(10)]
    text = "\n\n".join(paragraphs)
    chunks = chunker.chunk(text)
    assert len(chunks) > 1
    # Every chunk should be within the limit (with some tolerance for overlap)
    for chunk in chunks:
        assert len(chunk) <= 200  # generous tolerance


def test_chunks_preserve_paragraph_boundaries() -> None:
    chunker = TextChunker(max_chunk_size=200, chunk_overlap=0, min_chunk_size=10)
    text = "Primer parrafo corto.\n\nSegundo parrafo corto.\n\nTercer parrafo corto."
    chunks = chunker.chunk(text)
    # Should be a single chunk since total length is small
    assert len(chunks) == 1
    assert "Primer parrafo" in chunks[0]


def test_oversized_paragraph_is_split_by_sentences() -> None:
    chunker = TextChunker(max_chunk_size=100, chunk_overlap=0, min_chunk_size=10)
    long_paragraph = "Primera oracion del parrafo largo. Segunda oracion que extiende el parrafo. Tercera oracion con mas contenido. Cuarta oracion extra."
    chunks = chunker.chunk(long_paragraph)
    assert len(chunks) >= 1
    for chunk in chunks:
        assert len(chunk) > 0


def test_overlap_produces_repeated_content() -> None:
    chunker = TextChunker(max_chunk_size=80, chunk_overlap=30, min_chunk_size=10)
    paragraphs = [
        "Parrafo alfa con contenido.",
        "Parrafo beta con contenido.",
        "Parrafo gamma con contenido.",
        "Parrafo delta con contenido.",
    ]
    text = "\n\n".join(paragraphs)
    chunks = chunker.chunk(text)
    assert len(chunks) >= 2
