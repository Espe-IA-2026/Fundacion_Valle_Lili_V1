"""Tests unitarios offline para rag.retriever.KnowledgeRetriever."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from langchain_core.documents import Document


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_result(content: str, score: float) -> tuple[Document, float]:
    """Crea una tupla (Document, score) como las que devuelve ChromaDB."""
    doc = Document(
        page_content=content,
        metadata={"slug": "test-doc", "category": "01_servicios"},
    )
    return (doc, score)


# ── Fixture: mock de la base vectorial ────────────────────────────────────────

@pytest.fixture()
def mock_db() -> MagicMock:
    """MagicMock que simula una instancia de Chroma."""
    return MagicMock()


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_search_filtra_por_score_threshold(mock_db: MagicMock) -> None:
    """search devuelve solo los documentos cuyo score supera el umbral."""
    from rag.retriever import KnowledgeRetriever

    mock_db.similarity_search_with_relevance_scores.return_value = [
        _make_result("Alta relevancia", 0.8),
        _make_result("Baja relevancia", 0.2),
        _make_result("Relevancia media", 0.5),
    ]
    retriever = KnowledgeRetriever(mock_db)

    results = retriever.search("cardiología", k=5, score_threshold=0.3)

    assert len(results) == 2
    contents = [doc.page_content for doc in results]
    assert "Alta relevancia" in contents
    assert "Relevancia media" in contents
    assert "Baja relevancia" not in contents


def test_search_retorna_lista_vacia_cuando_todos_bajo_umbral(mock_db: MagicMock) -> None:
    """search devuelve lista vacía cuando ningún score supera el umbral."""
    from rag.retriever import KnowledgeRetriever

    mock_db.similarity_search_with_relevance_scores.return_value = [
        _make_result("Contenido irrelevante A", 0.1),
        _make_result("Contenido irrelevante B", 0.05),
    ]
    retriever = KnowledgeRetriever(mock_db)

    results = retriever.search("trasplante renal", k=5, score_threshold=0.3)

    assert results == []


def test_search_retorna_todos_cuando_todos_sobre_umbral(mock_db: MagicMock) -> None:
    """search devuelve todos los documentos cuando todos superan el umbral."""
    from rag.retriever import KnowledgeRetriever

    mock_db.similarity_search_with_relevance_scores.return_value = [
        _make_result("Resultado A", 0.9),
        _make_result("Resultado B", 0.7),
        _make_result("Resultado C", 0.85),
    ]
    retriever = KnowledgeRetriever(mock_db)

    results = retriever.search("urgencias", k=5, score_threshold=0.3)

    assert len(results) == 3


def test_search_retorna_lista_vacia_cuando_db_sin_resultados(mock_db: MagicMock) -> None:
    """search devuelve lista vacía cuando ChromaDB no encuentra candidatos."""
    from rag.retriever import KnowledgeRetriever

    mock_db.similarity_search_with_relevance_scores.return_value = []
    retriever = KnowledgeRetriever(mock_db)

    results = retriever.search("query sin resultados", k=5, score_threshold=0.3)

    assert results == []


def test_search_pasa_k_correcto_a_db(mock_db: MagicMock) -> None:
    """search invoca similarity_search_with_relevance_scores con el k indicado."""
    from rag.retriever import KnowledgeRetriever

    mock_db.similarity_search_with_relevance_scores.return_value = []
    retriever = KnowledgeRetriever(mock_db)

    retriever.search("oncología", k=8, score_threshold=0.3)

    mock_db.similarity_search_with_relevance_scores.assert_called_once_with(
        "oncología", k=8
    )


def test_search_incluye_resultado_con_score_igual_al_umbral(mock_db: MagicMock) -> None:
    """search incluye documentos cuyo score es exactamente igual al umbral (>=)."""
    from rag.retriever import KnowledgeRetriever

    mock_db.similarity_search_with_relevance_scores.return_value = [
        _make_result("Exactamente en el límite", 0.3),
    ]
    retriever = KnowledgeRetriever(mock_db)

    results = retriever.search("sedes", k=5, score_threshold=0.3)

    assert len(results) == 1
    assert results[0].page_content == "Exactamente en el límite"