"""Tests unitarios offline para app_agent.engine."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, ToolMessage

# ── Fixture: resetear singleton entre tests ───────────────────────────────────


@pytest.fixture(autouse=True)
def reset_agent_singleton() -> None:
    """Reinicia el singleton _agent a None antes y después de cada test.

    El módulo engine.py mantiene _agent como variable de módulo. Sin este
    reset, un test que inicialice el singleton contaminaría los siguientes.
    """
    mod_name = "app_agent.engine"
    if mod_name in sys.modules:
        sys.modules[mod_name]._agent = None
    yield
    if mod_name in sys.modules:
        sys.modules[mod_name]._agent = None


# ── Tests de get_rag_agent ────────────────────────────────────────────────────


def test_get_rag_agent_retorna_instancia() -> None:
    """get_rag_agent retorna la instancia producida por build_rag_agent."""
    mock_agent = MagicMock()

    with patch("app_agent.engine.build_rag_agent", return_value=mock_agent):
        from app_agent.engine import get_rag_agent
        result = get_rag_agent()

    assert result is mock_agent


def test_get_rag_agent_es_singleton() -> None:
    """get_rag_agent retorna la misma instancia en llamadas consecutivas.

    build_rag_agent solo debe invocarse una vez durante la vida del proceso;
    las llamadas siguientes reutilizan la instancia ya compilada.
    """
    mock_agent = MagicMock()

    with patch("app_agent.engine.build_rag_agent", return_value=mock_agent) as mock_build:
        from app_agent.engine import get_rag_agent
        first = get_rag_agent()
        second = get_rag_agent()

    assert first is second
    mock_build.assert_called_once()


def test_get_rag_agent_force_rebuild_reconstruye() -> None:
    """get_rag_agent con force_rebuild=True descarta el caché y crea una nueva instancia.

    Esto es útil tras re-indexar el knowledge base con 'build-index --force',
    cuando el agente debe cargar el índice ChromaDB actualizado.
    """
    first_agent = MagicMock(name="agent_v1")
    second_agent = MagicMock(name="agent_v2")

    with patch("app_agent.engine.build_rag_agent", side_effect=[first_agent, second_agent]) as mock_build:
        from app_agent.engine import get_rag_agent
        a1 = get_rag_agent()
        a2 = get_rag_agent(force_rebuild=True)

    assert a1 is first_agent
    assert a2 is second_agent
    assert mock_build.call_count == 2


# ── Tests de stream_agent_response ───────────────────────────────────────────


def test_stream_agent_response_yield_respuesta_final() -> None:
    """stream_agent_response emite el contenido del AIMessage final del agente."""
    final_msg = AIMessage(content="Respuesta institucional de la FVL.")
    mock_agent = MagicMock()
    mock_agent.stream.return_value = [
        {"messages": [final_msg]},
    ]

    with patch("app_agent.engine.build_rag_agent", return_value=mock_agent):
        from app_agent.engine import stream_agent_response
        results = list(stream_agent_response("¿Qué servicios tiene la FVL?", "thread-abc"))

    assert results == ["Respuesta institucional de la FVL."]


def test_stream_agent_response_filtra_tool_messages() -> None:
    """stream_agent_response descarta ToolMessages intermedios del ciclo ReACT.

    Los ToolMessages son resultados internos de herramientas, no respuestas
    destinadas al usuario final.
    """
    tool_msg = ToolMessage(content="resultado de herramienta", tool_call_id="call-1")
    final_msg = AIMessage(content="Respuesta final del agente.")
    mock_agent = MagicMock()
    mock_agent.stream.return_value = [
        {"messages": [tool_msg]},
        {"messages": [final_msg]},
    ]

    with patch("app_agent.engine.build_rag_agent", return_value=mock_agent):
        from app_agent.engine import stream_agent_response
        results = list(stream_agent_response("pregunta", "thread-abc"))

    assert results == ["Respuesta final del agente."]
    assert "resultado de herramienta" not in results


def test_stream_agent_response_filtra_ai_messages_con_tool_calls() -> None:
    """stream_agent_response descarta AIMessages que aún tienen tool_calls pendientes.

    Un AIMessage con tool_calls indica que el LLM ha decidido invocar una
    herramienta pero aún no ha sintetizado la respuesta final al usuario.
    """
    ai_with_calls = AIMessage(
        content="Voy a buscar esa información...",
        tool_calls=[{
            "id": "call-1",
            "name": "retrieve_fvl_knowledge",
            "args": {"query": "cardiología"},
            "type": "tool_call",
        }],
    )
    final_msg = AIMessage(content="Respuesta después de recuperar los documentos.")
    mock_agent = MagicMock()
    mock_agent.stream.return_value = [
        {"messages": [ai_with_calls]},
        {"messages": [final_msg]},
    ]

    with patch("app_agent.engine.build_rag_agent", return_value=mock_agent):
        from app_agent.engine import stream_agent_response
        results = list(stream_agent_response("pregunta", "thread-abc"))

    assert results == ["Respuesta después de recuperar los documentos."]
    assert "Voy a buscar" not in results


def test_stream_agent_response_pasa_thread_id_en_config() -> None:
    """stream_agent_response invoca agent.stream con el thread_id en el config.

    El thread_id es la clave que usa el checkpointer para aislar y recuperar
    el historial de conversación de cada sesión de usuario.
    """
    mock_agent = MagicMock()
    mock_agent.stream.return_value = []

    with patch("app_agent.engine.build_rag_agent", return_value=mock_agent):
        from app_agent.engine import stream_agent_response
        list(stream_agent_response("consulta", "uuid-sesion-xyz"))

    config_passed = mock_agent.stream.call_args.args[1]
    assert config_passed == {"configurable": {"thread_id": "uuid-sesion-xyz"}}


def test_stream_agent_response_eps_usa_json_sin_construir_agente() -> None:
    """Las consultas sobre EPS se resuelven con datos estructurados, no con ChromaDB."""
    structured_info = (
        "PREGUNTAS FRECUENTES:\n"
        "  P: ¿Qué EPS tienen convenio con la FVL?\n"
        "  R: La FVL atiende pacientes de múltiples EPS. Para verificar su EPS específica, "
        "comuníquese al +57 (2) 331 7000.\n"
    )
    mock_structured_tool = MagicMock()
    mock_structured_tool.invoke.return_value = structured_info

    with (
        patch("app_agent.engine.get_fvl_structured_info", mock_structured_tool),
        patch("app_agent.engine.build_rag_agent") as mock_build,
    ):
        from app_agent.engine import stream_agent_response
        results = list(stream_agent_response("¿Qué EPS tienen convenio?", "thread-abc"))

    assert len(results) == 1
    assert "múltiples EPS" in results[0]
    assert "_Fuente: datos institucionales_" in results[0]
    mock_structured_tool.invoke.assert_called_once_with({"query": "¿Qué EPS tienen convenio?"})
    mock_build.assert_not_called()


def test_stream_agent_events_eps_emite_tool_estructurada_sin_rag() -> None:
    """La UI debe mostrar la tool estructurada cuando la pregunta es sobre EPS."""
    structured_info = (
        "PREGUNTAS FRECUENTES:\n"
        "  P: ¿Qué EPS tienen convenio con la FVL?\n"
        "  R: La FVL atiende pacientes de múltiples EPS.\n"
    )
    mock_structured_tool = MagicMock()
    mock_structured_tool.invoke.return_value = structured_info

    with (
        patch("app_agent.engine.get_fvl_structured_info", mock_structured_tool),
        patch("app_agent.engine.build_rag_agent") as mock_build,
    ):
        from app_agent.engine import stream_agent_events
        events = list(stream_agent_events("EPS en convenio", "thread-abc"))

    assert events[0] == {"type": "thought", "tool": "get_fvl_structured_info", "text": ""}
    assert events[1]["type"] == "answer"
    assert "múltiples EPS" in events[1]["text"]
    mock_build.assert_not_called()


def test_stream_agent_response_yield_mensaje_error_en_excepcion() -> None:
    """stream_agent_response emite un mensaje amigable cuando el agente lanza una excepción.

    Garantiza que el usuario recibe retroalimentación incluso ante fallos
    de red, timeout o errores internos del agente.
    """
    mock_agent = MagicMock()
    mock_agent.stream.side_effect = RuntimeError("fallo de conexión simulado")

    with patch("app_agent.engine.build_rag_agent", return_value=mock_agent):
        from app_agent.engine import stream_agent_response
        results = list(stream_agent_response("pregunta", "thread-abc"))

    assert len(results) == 1
    assert "error" in results[0].lower() or "ocurrió" in results[0].lower()
