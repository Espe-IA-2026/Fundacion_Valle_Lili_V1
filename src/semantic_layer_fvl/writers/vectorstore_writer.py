from __future__ import annotations

import logging

from semantic_layer_fvl.config import Settings, get_settings
from semantic_layer_fvl.schemas import ProcessedDocument
from semantic_layer_fvl.vectorstore.store import VectorStore

logger = logging.getLogger(__name__)


class VectorStoreWriter:
    """Writes processed documents into the ChromaDB vector store."""

    def __init__(self, settings: Settings | None = None, store: VectorStore | None = None) -> None:
        self.settings = settings or get_settings()
        self._store = store

    @property
    def store(self) -> VectorStore:
        if self._store is None:
            self._store = VectorStore(settings=self.settings)
        return self._store

    def write(self, document: ProcessedDocument) -> None:
        self.store.upsert(document)
