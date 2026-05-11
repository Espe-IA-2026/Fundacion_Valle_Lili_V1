"""Herramienta de recuperación semántica para el agente RAG de la FVL."""

from __future__ import annotations

import logging

from langchain.tools import tool

from rag.indexer import KnowledgeIndexer
from rag.retriever import KnowledgeRetriever
from semantic_layer_fvl.config import get_settings

logger = logging.getLogger(__name__)

# Singleton a nivel de módulo — None hasta la primera llamada a la tool.
_retriever: KnowledgeRetriever | None = None


def _get_retriever() -> KnowledgeRetriever:
    """Devuelve el retriever, inicializándolo en la primera llamada.

    Carga el índice ChromaDB una sola vez durante la vida del proceso.
    Las llamadas siguientes reutilizan la instancia ya creada.

    Returns:
        Instancia de ``KnowledgeRetriever`` con el índice ChromaDB cargado.

    Raises:
        ValueError: Si no hay archivos ``.md`` en el directorio de conocimiento.
    """
    global _retriever
    if _retriever is None:
        logger.info("Inicializando KnowledgeRetriever por primera vez...")
        indexer = KnowledgeIndexer()
        db = indexer.build_or_load()
        _retriever = KnowledgeRetriever(db)
        logger.info("KnowledgeRetriever listo.")
    return _retriever


@tool
def retrieve_fvl_knowledge(query: str) -> str:
    """Busca información institucional de la Fundación Valle del Lili (FVL).

    Usa esta herramienta para cualquier pregunta sobre servicios médicos,
    especialidades, sedes, procedimientos, horarios, contactos o datos
    institucionales de la FVL. Devuelve fragmentos de documentos oficiales
    relevantes para la consulta.

    Args:
        query: Pregunta o tema a buscar en la base de conocimiento.

    Returns:
        Fragmentos de documentos institucionales relevantes separados por
        delimitadores. Si no hay resultados, devuelve un mensaje indicativo
        para que el agente lo comunique al usuario.
    """
    settings = get_settings()
    retriever = _get_retriever()

    docs = retriever.search(
        query,
        k=settings.rag_top_k,
        score_threshold=settings.rag_score_threshold,
    )

    if not docs:
        logger.debug("retrieve_fvl_knowledge: sin resultados para '%s'", query)
        return (
            "No encontré información relevante en la base de conocimiento "
            "para esta consulta."
        )

    parts: list[str] = []
    for i, doc in enumerate(docs, start=1):
        slug = doc.metadata.get("slug", "desconocido")
        category = doc.metadata.get("category", "")
        header = f"[Fragmento {i} — {slug}"
        if category:
            header += f" ({category})"
        header += "]"
        parts.append(f"{header}\n{doc.page_content}")

    logger.debug(
        "retrieve_fvl_knowledge: %d fragmentos recuperados para '%s'",
        len(parts),
        query,
    )
    return "\n\n---\n\n".join(parts)