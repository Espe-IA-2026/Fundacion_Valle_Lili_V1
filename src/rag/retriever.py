from __future__ import annotations

import logging

from langchain_chroma import Chroma
from langchain_core.documents import Document

logger = logging.getLogger(__name__)


class KnowledgeRetriever:
    """Realiza búsqueda semántica sobre el índice ChromaDB."""

    def __init__(self, db: Chroma) -> None:
        self._db = db

    def search(self, query: str, k: int = 5, score_threshold: float = 0.3) -> list[Document]:
        """Retorna los chunks más relevantes para la consulta.

        Args:
            query: Texto de la pregunta o tema a buscar.
            k: Número máximo de chunks a recuperar.
            score_threshold: Similitud mínima (0–1) para incluir un chunk.
        """
        results = self._db.similarity_search_with_relevance_scores(query, k=k)
        filtered = [doc for doc, score in results if score >= score_threshold]
        if not filtered:
            logger.debug("Ningún chunk superó el umbral %.2f para: %s", score_threshold, query)
        return filtered