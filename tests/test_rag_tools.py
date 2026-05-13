"""Tests unitarios offline para app_agent.tools."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from langchain_core.documents import Document


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_doc(content: str, slug: str = "test-slug", category: str = "01_servicios") -> Document:
    """Crea un Document con metadatos mínimos para los tests de la herramienta."""
    return Document(page_content=content, metadata={"slug": slug, "category": category})


def _mock_settings(top_k: int = 5, threshold: float = 0.3) -> MagicMock:
    """Crea un mock de Settings con los parámetros RAG configurados."""
    settings = MagicMock()
    settings.rag_top_k = top_k
    settings.rag_score_threshold = threshold
    return settings


# ── Tests de metadatos de la tool ─────────────────────────────────────────────


def test_retrieve_fvl_knowledge_es_langchain_tool() -> None:
    """retrieve_fvl_knowledge expone el contrato de herramienta LangChain.

    Verifica que el decorador @tool generó correctamente el nombre y la
    descripción que el agente LangChain usa para decidir cuándo invocarla.
    """
    from app_agent.tools import retrieve_fvl_knowledge

    assert retrieve_fvl_knowledge.name == "retrieve_fvl_knowledge"
    assert len(retrieve_fvl_knowledge.description) > 10
    assert "FVL" in retrieve_fvl_knowledge.description or "Fundación" in retrieve_fvl_knowledge.description


# ── Tests de comportamiento sin resultados ────────────────────────────────────


def test_retrieve_retorna_mensaje_cuando_no_hay_resultados() -> None:
    """retrieve_fvl_knowledge devuelve mensaje indicativo cuando el retriever no encuentra docs.

    Esto permite al agente comunicar al usuario que no hay información
    disponible en lugar de inventar una respuesta.
    """
    mock_retriever = MagicMock()
    mock_retriever.search.return_value = []

    with patch("app_agent.tools.get_settings", return_value=_mock_settings()), \
         patch("app_agent.tools._get_retriever", return_value=mock_retriever):
        from app_agent.tools import retrieve_fvl_knowledge
        result = retrieve_fvl_knowledge.invoke({"query": "pregunta sin resultados"})

    assert "No encontré información relevante" in result


# ── Tests de formato de salida ────────────────────────────────────────────────


def test_retrieve_formatea_fragmento_con_slug_y_categoria() -> None:
    """retrieve_fvl_knowledge incluye slug y categoría en el header del fragmento.

    El header permite al agente citar la fuente en el formato DOC:<slug>.
    """
    mock_retriever = MagicMock()
    mock_retriever.search.return_value = [
        _make_doc("Contenido de cardiología.", slug="cardiologia", category="01_servicios"),
    ]

    with patch("app_agent.tools.get_settings", return_value=_mock_settings()), \
         patch("app_agent.tools._get_retriever", return_value=mock_retriever):
        from app_agent.tools import retrieve_fvl_knowledge
        result = retrieve_fvl_knowledge.invoke({"query": "cardiología"})

    # El código elimina el prefijo numérico '01_' → devuelve solo 'servicios'
    assert "[Fragmento 1 — cardiologia (servicios)]" in result
    assert "Contenido de cardiología." in result


def test_retrieve_formatea_header_sin_categoria_cuando_esta_vacia() -> None:
    """retrieve_fvl_knowledge omite el paréntesis de categoría cuando el campo está vacío."""
    mock_retriever = MagicMock()
    mock_retriever.search.return_value = [
        Document(page_content="Texto sin categoría.", metadata={"slug": "doc-sin-cat", "category": ""}),
    ]

    with patch("app_agent.tools.get_settings", return_value=_mock_settings()), \
         patch("app_agent.tools._get_retriever", return_value=mock_retriever):
        from app_agent.tools import retrieve_fvl_knowledge
        result = retrieve_fvl_knowledge.invoke({"query": "consulta"})

    assert "[Fragmento 1 — doc-sin-cat]" in result
    assert "[Fragmento 1 — doc-sin-cat (" not in result


def test_retrieve_separa_multiples_fragmentos_con_delimitador() -> None:
    """retrieve_fvl_knowledge une múltiples fragmentos con el separador '---'.

    El delimitador visual facilita que el agente identifique los límites
    entre documentos fuente al sintetizar su respuesta.
    """
    mock_retriever = MagicMock()
    mock_retriever.search.return_value = [
        _make_doc("Fragmento A.", slug="doc-a"),
        _make_doc("Fragmento B.", slug="doc-b"),
    ]

    with patch("app_agent.tools.get_settings", return_value=_mock_settings()), \
         patch("app_agent.tools._get_retriever", return_value=mock_retriever):
        from app_agent.tools import retrieve_fvl_knowledge
        result = retrieve_fvl_knowledge.invoke({"query": "consulta"})

    assert "\n\n---\n\n" in result
    assert "[Fragmento 1" in result
    assert "[Fragmento 2" in result


# ── Tests de parámetros de búsqueda ──────────────────────────────────────────


def test_retrieve_pasa_parametros_de_settings_al_search() -> None:
    """retrieve_fvl_knowledge invoca retriever.search con k y threshold tomados de Settings.

    Garantiza que los valores configurados en .env (RAG_TOP_K, RAG_SCORE_THRESHOLD)
    se propagan correctamente hasta la llamada de búsqueda semántica.
    """
    mock_retriever = MagicMock()
    mock_retriever.search.return_value = []
    custom_settings = _mock_settings(top_k=8, threshold=0.45)

    with patch("app_agent.tools.get_settings", return_value=custom_settings), \
         patch("app_agent.tools._get_retriever", return_value=mock_retriever):
        from app_agent.tools import retrieve_fvl_knowledge
        retrieve_fvl_knowledge.invoke({"query": "oncología"})

    mock_retriever.search.assert_called_once_with(
        "oncología", k=8, score_threshold=0.45
    )
