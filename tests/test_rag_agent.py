"""Tests unitarios offline para app_agent.agent."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from langgraph.checkpoint.memory import InMemorySaver


# ── Fixture compartido ────────────────────────────────────────────────────────


@pytest.fixture()
def mock_settings() -> MagicMock:
    """Settings mock con los campos mínimos requeridos por build_rag_agent."""
    settings = MagicMock()
    settings.openai_model = "gpt-4o-mini"
    settings.openai_api_key = "sk-test-key"
    return settings


# ── Tests de build_rag_agent ──────────────────────────────────────────────────


def test_build_rag_agent_retorna_objeto_compilado(mock_settings: MagicMock) -> None:
    """build_rag_agent retorna el objeto compilado por create_agent sin lanzar excepciones.

    Verifica el contrato de retorno: el resultado es la instancia producida
    por create_agent, lista para invocar con .stream() o .invoke().
    """
    mock_compiled_agent = MagicMock()

    with patch("app_agent.agent.get_settings", return_value=mock_settings), \
         patch("app_agent.agent.ChatOpenAI", return_value=MagicMock()), \
         patch("app_agent.agent.create_agent", return_value=mock_compiled_agent):
        from app_agent.agent import build_rag_agent
        result = build_rag_agent()

    assert result is mock_compiled_agent


def test_build_rag_agent_usa_tool_retrieve_fvl_knowledge(mock_settings: MagicMock) -> None:
    """build_rag_agent pasa retrieve_fvl_knowledge como herramienta a create_agent.

    El nombre de la herramienta debe coincidir con lo que el system prompt
    instruye al agente a invocar para búsquedas institucionales.
    """
    with patch("app_agent.agent.get_settings", return_value=mock_settings), \
         patch("app_agent.agent.ChatOpenAI", return_value=MagicMock()), \
         patch("app_agent.agent.create_agent") as mock_create_agent:
        mock_create_agent.return_value = MagicMock()
        from app_agent.agent import build_rag_agent
        build_rag_agent()

    tool_names = [t.name for t in mock_create_agent.call_args.kwargs["tools"]]
    assert "retrieve_fvl_knowledge" in tool_names


def test_build_rag_agent_incluye_checkpointer_inmemory(mock_settings: MagicMock) -> None:
    """build_rag_agent pasa un InMemorySaver como checkpointer a create_agent.

    El checkpointer es imprescindible para que el agente mantenga memoria
    de sesión diferenciada por thread_id sin pasarla desde la UI.
    """
    with patch("app_agent.agent.get_settings", return_value=mock_settings), \
         patch("app_agent.agent.ChatOpenAI", return_value=MagicMock()), \
         patch("app_agent.agent.create_agent") as mock_create_agent:
        mock_create_agent.return_value = MagicMock()
        from app_agent.agent import build_rag_agent
        build_rag_agent()

    checkpointer = mock_create_agent.call_args.kwargs["checkpointer"]
    assert isinstance(checkpointer, InMemorySaver)


def test_build_rag_agent_crea_modelo_con_temperatura_baja(mock_settings: MagicMock) -> None:
    """build_rag_agent instancia ChatOpenAI con temperatura 0.1 para respuestas deterministas.

    La temperatura baja reduce la variabilidad en respuestas institucionales
    donde la precisión factual es prioritaria sobre la creatividad.
    """
    with patch("app_agent.agent.get_settings", return_value=mock_settings), \
         patch("app_agent.agent.ChatOpenAI") as mock_chat_openai, \
         patch("app_agent.agent.create_agent", return_value=MagicMock()):
        mock_chat_openai.return_value = MagicMock()
        from app_agent.agent import build_rag_agent
        build_rag_agent()

    call_kwargs = mock_chat_openai.call_args.kwargs
    assert call_kwargs["temperature"] == 0.1
    assert call_kwargs["model"] == "gpt-4o-mini"


def test_build_rag_agent_registra_herramienta_datos_estructurados(mock_settings: MagicMock) -> None:
    """build_rag_agent registra get_fvl_structured_info como segunda herramienta.

    La herramienta de datos estructurados permite al agente responder preguntas
    directas (teléfonos, horarios, NIT) sin consultar el índice vectorial ChromaDB.
    Este camino determinista es el núcleo del enrutamiento de Módulo 2.
    """
    with patch("app_agent.agent.get_settings", return_value=mock_settings), \
         patch("app_agent.agent.ChatOpenAI", return_value=MagicMock()), \
         patch("app_agent.agent.create_agent") as mock_create_agent:
        mock_create_agent.return_value = MagicMock()
        from app_agent.agent import build_rag_agent
        build_rag_agent()

    tool_names = [t.name for t in mock_create_agent.call_args.kwargs["tools"]]
    assert "get_fvl_structured_info" in tool_names


def test_build_rag_agent_registra_exactamente_dos_herramientas(mock_settings: MagicMock) -> None:
    """build_rag_agent pasa exactamente dos herramientas a create_agent.

    El enrutador requiere dos caminos diferenciados: RAG (semántico) y datos
    estructurados (determinista). Más o menos herramientas indica un error de
    configuración del agente.
    """
    with patch("app_agent.agent.get_settings", return_value=mock_settings), \
         patch("app_agent.agent.ChatOpenAI", return_value=MagicMock()), \
         patch("app_agent.agent.create_agent") as mock_create_agent:
        mock_create_agent.return_value = MagicMock()
        from app_agent.agent import build_rag_agent
        build_rag_agent()

    tools_passed = mock_create_agent.call_args.kwargs["tools"]
    assert len(tools_passed) == 2
