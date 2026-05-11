"""Agente conversacional RAG para la Fundación Valle del Lili — Módulo 2.

Este paquete implementa la evolución desde el enfoque NO-RAG (Módulo 1,
context stuffing) hacia un agente con recuperación semántica dinámica
sobre el índice ChromaDB generado por ``rag.indexer.KnowledgeIndexer``.

Ciclo de vida del agente (ReACT):
    1. El usuario formula una pregunta.
    2. El LLM decide si invocar ``retrieve_fvl_knowledge``.
    3. La herramienta recupera chunks relevantes del índice vectorial.
    4. El LLM sintetiza una respuesta basada en los fragmentos recuperados.
    5. Si necesita más información, el ciclo se repite.

Piezas públicas:

- ``retrieve_fvl_knowledge``: herramienta LangChain de búsqueda semántica.
- ``build_rag_agent``: construye el agente con ``create_agent``.
- ``get_rag_agent``: singleton con lazy initialization del agente.
- ``stream_agent_response``: generador para streaming en la UI Streamlit.
"""

from __future__ import annotations

from app_agent.agent import build_rag_agent
from app_agent.engine import get_rag_agent, stream_agent_response
from app_agent.tools import retrieve_fvl_knowledge

__all__ = [
    "build_rag_agent",
    "retrieve_fvl_knowledge",
    "get_rag_agent",
    "stream_agent_response"
]