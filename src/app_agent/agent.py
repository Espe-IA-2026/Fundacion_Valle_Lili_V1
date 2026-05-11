"""Agente conversacional RAG para la Fundación Valle del Lili."""

from __future__ import annotations

import logging

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver


from app_agent.tools import retrieve_fvl_knowledge
from semantic_layer_fvl.config import get_settings

logger = logging.getLogger(__name__)

_AGENT_SYSTEM_PROMPT = (
    "Eres el asistente virtual oficial de la Fundación Valle del Lili (FVL), "
    "un hospital universitario de alta complejidad ubicado en Cali, Colombia. "
    "\n\n"
    "INSTRUCCIONES ESTRICTAS:\n"
    "1. Para CUALQUIER pregunta sobre servicios, especialidades, sedes, procedimientos, "
    "horarios, contactos o información institucional, USA SIEMPRE la herramienta "
    "retrieve_fvl_knowledge antes de generar tu respuesta.\n"
    "2. Basa tu respuesta ÚNICAMENTE en la información recuperada por la herramienta.\n"
    "3. Si la herramienta no devuelve información relevante, responde EXACTAMENTE: "
    "'No encontré esa información en los documentos institucionales disponibles.'\n"
    "4. NUNCA inventes datos como fechas, nombres de médicos, precios, horarios "
    "o teléfonos que no estén en los fragmentos recuperados.\n"
    "5. Responde en español, con tono profesional, amable y conciso.\n"
    "6. Indica de qué fragmento proviene la información cuando sea relevante "
    "usando el formato DOC:<slug>.\n"
    "7. Si el usuario saluda o hace preguntas ajenas a la institución, responde "
    "con cortesía pero redirige la conversación hacia tu función institucional."
)


def build_rag_agent():
    """Construye el agente RAG de la FVL con la herramienta de recuperación semántica.

    Crea un agente ReACT usando ``create_agent`` de LangChain, que internamente
    construye un grafo LangGraph con el ciclo: razonar → usar tool → razonar → responder.

    El modelo usa temperatura 0.1 para respuestas deterministas y fundamentadas.
    El system prompt instruye al agente a usar siempre ``retrieve_fvl_knowledge``
    antes de responder cualquier pregunta institucional.

    Returns:
        Agente compilado listo para invocar con ``.invoke()`` o transmitir
        con ``.stream()``. La entrada esperada es un dict con clave ``messages``.
    """
    settings = get_settings()
    model = ChatOpenAI(
        model=settings.openai_model,
        temperature=0.1,
        api_key=settings.openai_api_key,
    )
    agent = create_agent(
        model,
        tools=[retrieve_fvl_knowledge],
        system_prompt=_AGENT_SYSTEM_PROMPT,
        checkpointer=InMemorySaver(),
    )

    logger.info("Agente RAG construido correctamente.")
    return agent