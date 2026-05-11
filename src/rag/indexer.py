from __future__ import annotations

import logging
import re
import shutil
from pathlib import Path

import yaml
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

from semantic_layer_fvl.config import get_settings
from semantic_layer_fvl.processors.chunker import TextChunker

logger = logging.getLogger(__name__)

_FRONTMATTER_RE = re.compile(r"^---[\s\S]*?---\s*\n")
_FRONTMATTER_FIELDS_RE = re.compile(r"^---([\s\S]*?)---", re.MULTILINE)


class KnowledgeIndexer:
    """Indexa los documentos Markdown del knowledge base en ChromaDB."""

    COLLECTION_NAME = "fvl_knowledge"

    def __init__(self) -> None:
        settings = get_settings()
        self._knowledge_dir = settings.resolved_knowledge_dir
        self._chroma_dir = settings.resolved_chroma_persist_dir
        self._embeddings = OpenAIEmbeddings(model=settings.embedding_model)
        self._chunker = TextChunker(max_chunk_size=1000, chunk_overlap=200)
        self._db: Chroma | None = None

    def build_or_load(self, force: bool = False) -> Chroma:
        """Carga el índice existente o lo construye desde cero.

        Args:
            force: Si True, elimina el índice existente y re-indexa todo.

        Returns:
            Chroma: instancia de la base vectorial lista para consultas.
        """
        if force:
            self._drop_collection()

        if not force and self._index_exists():
            logger.info("Índice ChromaDB encontrado — cargando sin re-indexar.")
            self._db = Chroma(
                collection_name=self.COLLECTION_NAME,
                persist_directory=str(self._chroma_dir),
                embedding_function=self._embeddings,
            )
            return self._db

        logger.info("Construyendo índice ChromaDB desde cero...")
        documents = self._load_documents()
        self._db = Chroma.from_documents(
            documents=documents,
            embedding=self._embeddings,
            collection_name=self.COLLECTION_NAME,
            persist_directory=str(self._chroma_dir),
        )
        logger.info("Índice construido con %d chunks.", len(documents))
        return self._db

    @property
    def chunk_count(self) -> int:
        """Número de chunks almacenados en el índice actual."""
        if self._db is None:
            return 0
        return self._db._collection.count()

    def _index_exists(self) -> bool:
        chroma_marker = self._chroma_dir / "chroma.sqlite3"
        return chroma_marker.exists()

    def _drop_collection(self) -> None:
        if self._chroma_dir.exists():
            shutil.rmtree(self._chroma_dir)
            logger.info("Colección ChromaDB eliminada para re-indexar.")

    def _load_documents(self) -> list[Document]:
        md_files = list(self._knowledge_dir.rglob("*.md"))
        if not md_files:
            raise ValueError(
                f"No hay archivos .md en '{self._knowledge_dir}'. "
                "Ejecuta primero el pipeline ETL: "
                "uv run semantic-layer-fvl crawl-domain <dominio> --write"
            )

        docs: list[Document] = []
        for path in md_files:
            raw = path.read_text(encoding="utf-8")
            metadata = self._parse_frontmatter(raw)
            body = _FRONTMATTER_RE.sub("", raw).strip()
            chunks = self._chunker.chunk(body)
            for i, chunk in enumerate(chunks):
                docs.append(Document(
                    page_content=chunk,
                    metadata={**metadata, "chunk_index": i, "source_file": str(path)},
                ))
        return docs

    def _parse_frontmatter(self, raw: str) -> dict:
        match = _FRONTMATTER_FIELDS_RE.match(raw)
        if not match:
            return {}
        try:
            return yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError:
            return {}
