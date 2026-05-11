"""Motor de alto nivel para el agente RAG: singleton y streaming."""

from __future__ import annotations

import logging
from collections.abc import Iterator

from app_agent.agent import build_rag_agent

logger = logging.getLogger(__name__)

# Singleton a nivel de módulo — None hasta la primera llamada a get_rag_agent().
_agent = None


def get_rag_agent(force_rebuild: bool = False):
    """Devuelve el agente RAG con lazy initialization (singleton).

    La primera llamada construye el agente cargando el índice ChromaDB y
    compilando el grafo LangGraph. Las llamadas siguientes devuelven la
    instancia ya creada sin costo adicional.

    Args:
        force_rebuild: Si ``True``, descarta la instancia en caché y
            reconstruye el agente desde cero. Útil tras re-indexar el
            knowledge base con ``build-index --force``.

    Returns:
        Agente compilado listo para invocar o transmitir.
    """
    global _agent

    if _agent is None or force_rebuild:
        logger.info("Construyendo agente RAG (primera inicialización)...")
        _agent = build_rag_agent()
        logger.info("Agente RAG listo.")

    return _agent


def stream_agent_response(
    question: str,
    thread_id: str,
) -> Iterator[str]:
    """Genera la respuesta del agente fragmento a fragmento para streaming en Streamlit.

    Envía únicamente el mensaje actual al agente; el checkpointer recupera
    el historial del hilo identificado por ``thread_id`` de forma automática.
    Filtra los pasos intermedios (tool calls y ToolMessages) y emite solo
    la respuesta final del LLM.

    Args:
        question: Pregunta actual del usuario.
        thread_id: Identificador UUID de la sesión de conversación.
            El checkpointer usa este valor para aislar y recuperar el
            historial de cada sesión sin necesidad de pasarlo manualmente.

    Yields:
        Texto de la respuesta final del agente. Con ``stream_mode="values"``
        se entrega el mensaje completo en un único chunk cuando el agente
        termina de razonar.
    """
    agent = get_rag_agent()
    messages = [{"role": "user", "content": question}]
    config = {"configurable": {"thread_id": thread_id}}

    try:
        for step in agent.stream(
            {"messages": messages},
            config,
            stream_mode="values",
        ):
            last_msg = step["messages"][-1]
            content = getattr(last_msg, "content", None)
            tool_calls = getattr(last_msg, "tool_calls", None)

            # Solo emitir la respuesta final del agente:
            # debe tener content, no debe tener tool_calls pendientes
            # y no debe ser un ToolMessage (resultado de herramienta)
            if (
                content
                and isinstance(content, str)
                and not tool_calls
                and last_msg.__class__.__name__ == "AIMessage"
            ):
                yield content

    except Exception as exc:
        logger.exception("Error durante el stream del agente RAG: %s", exc)
        yield (
            "Lo siento, ocurrió un error al procesar tu consulta. "
            "Por favor intenta de nuevo."
        )