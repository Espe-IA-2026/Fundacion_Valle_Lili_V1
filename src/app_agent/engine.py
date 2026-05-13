"""Motor de alto nivel para el agente FVL: singleton, streaming y eventos de herramienta."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import TypedDict

from langchain_openai import ChatOpenAI

from app_agent.agent import build_rag_agent
from app_agent.tools import get_fvl_structured_info
from semantic_layer_fvl.config import get_settings

logger = logging.getLogger(__name__)

# Singleton a nivel de módulo — None hasta la primera llamada a get_rag_agent().
_agent = None

# Keywords que activan el enrutamiento directo al JSON estructurado.
# Se bypasea el ciclo ReACT del agente para estos casos deterministas.
_STRUCTURED_DIRECT_KEYWORDS = frozenset([
    # EPS y convenios
    "eps", "convenio", "convenios", "aseguradora", "aseguradoras",
    "medicina prepagada", "prepagada", "colmedica", "colmédica",
    "medisanitas", "colsanitas", "coomeva", "sura", "sanitas",
    "compensar", "nueva eps", "salud total", "allianz", "seguros bolivar",
    "seguros bolívar", "soat", "arl", "ecopetrol", "poliza", "póliza",
    # Horarios
    "horario", "horarios", "hora de atención", "hora de atencion",
    "atienden los sábados", "atienden los domingos",
    # Contactos
    "teléfono", "telefono", "número de teléfono", "numero de telefono",
    "correo", "email", "whatsapp", "extensión", "extension",
    "cómo los contacto", "cómo me comunico", "objetos perdidos", "pqrs",
    # Sedes y ubicación
    "sede", "sedes", "dirección", "direccion", "ubicación", "ubicacion",
    "dónde están", "donde estan", "dónde queda", "donde queda",
    # Datos institucionales
    "nit", "razón social", "razon social", "naturaleza juridica", "naturaleza jurídica",
    "acreditación", "acreditacion", "jci", "joint commission",
    # Métodos de pago y servicios de apoyo
    "método de pago", "metodo de pago", "métodos de pago", "metodos de pago",
    "forma de pago", "formas de pago",
    "parqueadero", "parqueaderos", "capilla", "restaurante", "banco de sangre",
    # Servicios digitales
    "telemedicina", "app fvl", "fvl responde",
])


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


def _should_use_structured_direct_route(question: str) -> bool:
    """Indica si la consulta debe resolverse contra el JSON estructurado.

    Detecta keywords que identifican consultas sobre datos concretos (EPS,
    horarios, contactos, sedes, NIT) y activa el enrutamiento determinista,
    bypaseando el ciclo ReACT del agente para evitar errores de routing del LLM.
    """
    normalized = question.casefold()
    return any(keyword in normalized for keyword in _STRUCTURED_DIRECT_KEYWORDS)


def _synthesize_structured_answer(question: str, structured_info: str) -> str:
    """Sintetiza una respuesta natural usando el LLM con los datos estructurados como contexto.

    Se invoca cuando el pre-router detecta una consulta sobre datos concretos.
    El LLM recibe los datos ya recuperados del JSON y solo necesita redactar
    la respuesta, sin necesidad de elegir herramientas.

    Args:
        question: Pregunta original del usuario.
        structured_info: Datos formateados devueltos por get_fvl_structured_info.

    Returns:
        Respuesta sintetizada en lenguaje natural con cita de fuente.
    """
    if structured_info.startswith(("No se encontró", "Error al leer")):
        return structured_info

    settings = get_settings()
    llm = ChatOpenAI(
        model=settings.openai_model,
        temperature=0.1,
        api_key=settings.openai_api_key,
    )
    messages = [
        {
            "role": "system",
            "content": (
                "Eres el asistente virtual oficial de la Fundación Valle del Lili (FVL), "
                "un hospital universitario de alta complejidad en Cali, Colombia. "
                "Responde la pregunta del usuario usando ÚNCICAMENTE los datos institucionales proporcionados. "
                "Sé claro, profesional y conciso. No inventes ni extrapoles datos. "
                "Al final de tu respuesta incluye siempre: _Fuente: datos institucionales_"
            ),
        },
        {
            "role": "user",
            "content": (
                f"DATOS INSTITUCIONALES DISPONIBLES:\n\n{structured_info}\n\n"
                f"PREGUNTA: {question}"
            ),
        },
    ]
    try:
        response = llm.invoke(messages)
        return response.content
    except Exception as exc:
        logger.exception("Error al sintetizar respuesta estructurada: %s", exc)
        # Fallback: devolver los datos crudos si el LLM falla
        return f"{structured_info}\n\n_Fuente: datos institucionales_"


def _get_direct_structured_answer(question: str) -> str | None:
    """Devuelve una respuesta sintetizada si la consulta pertenece al JSON estructurado."""
    if not _should_use_structured_direct_route(question):
        return None

    structured_info = get_fvl_structured_info.invoke({"query": question})
    return _synthesize_structured_answer(question, structured_info)


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
    direct_answer = _get_direct_structured_answer(question)
    if direct_answer:
        yield direct_answer
        return

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


class AgentEvent(TypedDict):
    """Evento emitido por el agente durante el ciclo ReACT."""

    type: str   # "thought" | "answer" | "error"
    tool: str   # nombre de la herramienta invocada (solo cuando type == "thought")
    text: str   # contenido del mensaje (solo cuando type == "answer" o "error")


def stream_agent_events(
    question: str,
    thread_id: str,
) -> Iterator[AgentEvent]:
    """Genera eventos del agente: pensamientos (herramienta elegida) y respuesta final.

    A diferencia de ``stream_agent_response``, este generador emite dicts tipados
    que permiten a la UI distinguir qué herramienta eligió el agente y mostrar
    el razonamiento antes de la respuesta final.

    Tipos de evento emitidos:

    - ``{"type": "thought", "tool": "<nombre>", "text": ""}`` — el agente decidió
      invocar una herramienta; se emite uno por cada tool call en el turno.
    - ``{"type": "answer", "text": "<respuesta>", "tool": ""}`` — respuesta final
      del agente lista para mostrar al usuario.
    - ``{"type": "error", "text": "<msg>", "tool": ""}`` — error irrecuperable
      durante el stream; la UI debe mostrarlo como respuesta de fallback.

    Args:
        question: Pregunta actual del usuario.
        thread_id: Identificador UUID de la sesión de conversación.

    Yields:
        ``AgentEvent`` con los campos ``type``, ``tool`` y ``text``.
    """
    if _should_use_structured_direct_route(question):
        yield AgentEvent(type="thought", tool="get_fvl_structured_info", text="")
        structured_info = get_fvl_structured_info.invoke({"query": question})
        answer = _synthesize_structured_answer(question, structured_info)
        yield AgentEvent(type="answer", tool="", text=answer)
        return

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

            # El agente decide invocar herramienta(s) — emitir un "thought" por cada una
            if tool_calls and last_msg.__class__.__name__ == "AIMessage":
                for tc in tool_calls:
                    if isinstance(tc, dict):
                        tool_name = tc.get("name", "herramienta")
                    else:
                        tool_name = getattr(tc, "name", "herramienta")
                    yield AgentEvent(type="thought", tool=tool_name, text="")

            # Respuesta final del agente (sin tool_calls pendientes)
            elif (
                content
                and isinstance(content, str)
                and not tool_calls
                and last_msg.__class__.__name__ == "AIMessage"
            ):
                yield AgentEvent(type="answer", tool="", text=content)

    except Exception as exc:
        logger.exception("Error durante stream_agent_events: %s", exc)
        yield AgentEvent(
            type="error",
            tool="",
            text=(
                "Lo siento, ocurrió un error al procesar tu consulta. "
                "Por favor intenta de nuevo."
            ),
        )
