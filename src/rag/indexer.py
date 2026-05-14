from __future__ import annotations

import logging
import re
import shutil

import yaml
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

from semantic_layer_fvl.config import get_settings
from semantic_layer_fvl.processors.chunker import TextChunker

logger = logging.getLogger(__name__)

_FRONTMATTER_RE = re.compile(r"^---[\s\S]*?---\s*\n")
_FRONTMATTER_FIELDS_RE = re.compile(r"^---([\s\S]*?)---", re.MULTILINE)

# Etiquetas legibles por categoría para el prefijo de contexto de cada chunk.
# Convierte códigos internos ("02_servicios") en términos semánticos que
# mejoran la precisión de los embeddings en búsquedas factuales.
_CATEGORY_LABELS: dict[str, str] = {
    "01_organizacion": "Información Institucional",
    "02_servicios": "Servicios Médicos",
    "03_talento_humano": "Directorio de Especialistas",
    "04_sedes_ubicaciones": "Sedes y Ubicaciones",
    "09_noticias": "Noticias y Novedades",
    "10_multimedia": "Contenido Multimedia",
}

# Longitud mínima del cuerpo (sin frontmatter) para que un documento sea indexado.
# Evita almacenar chunks vacíos o con solo títulos que no aportan valor semántico.
_MIN_BODY_CHARS = 60


class KnowledgeIndexer:
    """Indexa los documentos Markdown del knowledge base en ChromaDB.

    Aplica *contextual enrichment*: cada chunk incluye un prefijo con el nombre
    de la institución, la categoría y el título del documento de origen. Esto
    mejora la precisión del embedding especialmente en documentos cortos (p.ej.
    perfiles de especialistas) donde el cuerpo por sí solo carece de contexto.
    """

    COLLECTION_NAME = "fvl_knowledge"

    def __init__(self) -> None:
        settings = get_settings()
        self._knowledge_dir = settings.resolved_knowledge_dir
        self._chroma_dir = settings.resolved_chroma_persist_dir
        self._embeddings = OpenAIEmbeddings(
            model=settings.embedding_model,
            api_key = settings.openai_api_key,
        )
        self._chunker = TextChunker(max_chunk_size=900, chunk_overlap=150)
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
        """Carga todos los archivos .md del knowledge base y los fragmenta en chunks.

        Para cada archivo:
        1. Extrae el frontmatter YAML y sanea los metadatos para ChromaDB.
        2. Filtra documentos con cuerpo demasiado corto (< ``_MIN_BODY_CHARS``).
        3. Construye un prefijo de contexto institucional con título y categoría.
        4. Divide el cuerpo en chunks solapados y añade el prefijo a cada uno.

        El prefijo de contexto (*contextual enrichment*) garantiza que incluso
        chunks cortos (p.ej. perfiles de especialistas con solo keywords)
        contengan suficiente información institucional para producir embeddings
        semánticamente precisos.

        Returns:
            Lista de ``Document`` enriquecidos con contenido y metadatos.

        Raises:
            ValueError: Si no hay archivos ``.md`` en ``knowledge_dir``.
        """
        md_files = list(self._knowledge_dir.rglob("*.md"))
        if not md_files:
            raise ValueError(
                f"No hay archivos .md en '{self._knowledge_dir}'. "
                "Ejecuta primero el pipeline ETL: "
                "uv run semantic-layer-fvl crawl-domain <dominio> --write"
            )

        docs: list[Document] = []
        skipped = 0
        for path in md_files:
            raw = path.read_text(encoding="utf-8")
            raw_metadata = self._parse_frontmatter(raw)
            metadata = self._sanitize_metadata(raw_metadata)
            body = _FRONTMATTER_RE.sub("", raw).strip()

            # Omitir documentos con contenido insuficiente
            if len(body) < _MIN_BODY_CHARS:
                logger.debug(
                    "Documento omitido (cuerpo < %d chars): %s", _MIN_BODY_CHARS, path.name
                )
                skipped += 1
                continue

            context_prefix = self._build_context_prefix(raw_metadata)
            chunks = self._chunker.chunk(body)
            total = len(chunks)

            for i, chunk in enumerate(chunks):
                # Prepend institutional context so every chunk carries its origin
                enriched = f"{context_prefix}\n\n{chunk}" if context_prefix else chunk
                docs.append(Document(
                    page_content=enriched,
                    metadata={
                        **metadata,
                        "chunk_index": i,
                        "total_chunks": total,
                        "source_file": str(path),
                    },
                ))

        if skipped:
            logger.info(
                "Documentos omitidos (contenido insuficiente): %d de %d",
                skipped, len(md_files),
            )
        logger.info(
            "Documentos indexados: %d | Chunks generados: %d",
            len(md_files) - skipped, len(docs),
        )
        return docs

    @staticmethod
    def _build_context_prefix(raw_metadata: dict) -> str:
        """Construye el prefijo de contexto institucional para enriquecer cada chunk.

        Formato: ``Fundación Valle del Lili | {etiqueta_categoría} | {título}``

        Este prefijo permite al modelo de embeddings anclar semánticamente
        cada fragmento a su documento de origen sin necesidad de ver el
        frontmatter completo. Es especialmente valioso para documentos cortos
        (perfiles de especialistas, noticias) donde el cuerpo solo contiene
        términos médicos sin contexto institucional.

        Ejemplo para especialista:
            ``Fundación Valle del Lili | Directorio de Especialistas | Dr. Juan Pérez``

        Ejemplo para servicio:
            ``Fundación Valle del Lili | Servicios Médicos | Cardiología``

        Args:
            raw_metadata: Diccionario del frontmatter YAML del documento.

        Returns:
            Cadena de prefijo contextual lista para anteponer al chunk.
        """
        title = raw_metadata.get("title", "")
        category = str(raw_metadata.get("category", ""))
        category_label = _CATEGORY_LABELS.get(
            category,
            category.split("_", 1)[-1].capitalize() if "_" in category else category,
        )

        parts = ["Fundación Valle del Lili"]
        if category_label:
            parts.append(category_label)
        if title:
            parts.append(title)

        return " | ".join(parts)

    def _sanitize_metadata(self, raw: dict) -> dict:
        """Convierte los valores del frontmatter a tipos aceptados por ChromaDB.

        ChromaDB solo acepta ``str``, ``int``, ``float`` y ``bool`` como valores
        de metadata. Este método normaliza los tipos problemáticos:

        - Listas no vacías → string separado por comas.
        - Listas vacías → se omiten.
        - ``None`` → se omite.
        - ``datetime``, ``AnyHttpUrl`` y otros objetos → ``str(valor)``.

        Args:
            raw: Diccionario de metadata tal como lo devuelve ``_parse_frontmatter``.

        Returns:
            Diccionario con solo tipos escalares aceptados por ChromaDB.
        """
        sanitized: dict = {}
        for key, value in raw.items():
            if value is None:
                continue
            if isinstance(value, list):
                if value:
                    sanitized[key] = ", ".join(str(v) for v in value)
                # lista vacía → se omite
            elif isinstance(value, bool):
                sanitized[key] = value
            elif isinstance(value, (int, float)):
                sanitized[key] = value
            elif isinstance(value, str):
                sanitized[key] = value
            else:
                # datetime, AnyHttpUrl, objetos Pydantic, etc.
                sanitized[key] = str(value)
        return sanitized

    def _parse_frontmatter(self, raw: str) -> dict:
        match = _FRONTMATTER_FIELDS_RE.match(raw)
        if not match:
            return {}
        try:
            return yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError:
            return {}
