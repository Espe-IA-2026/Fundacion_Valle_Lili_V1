from __future__ import annotations

from fastapi import APIRouter, Query

from semantic_layer_fvl.orchestrator import SemanticPipeline
from semantic_layer_fvl.schemas import SearchResult

router = APIRouter(tags=["knowledge"])

_pipeline: SemanticPipeline | None = None


def _get_pipeline() -> SemanticPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = SemanticPipeline()
    return _pipeline


@router.get("/search", response_model=list[SearchResult])
def search(
    q: str = Query(..., min_length=1, description="Texto de búsqueda semántica"),
    limit: int = Query(default=5, ge=1, le=50, description="Cantidad máxima de resultados"),
) -> list[SearchResult]:
    """Búsqueda semántica sobre el knowledge base indexado."""
    pipeline = _get_pipeline()
    return pipeline.search(q, n_results=limit)


@router.get("/stats")
def stats() -> dict:
    """Estadísticas del knowledge base."""
    pipeline = _get_pipeline()

    from semantic_layer_fvl.vectorstore.store import VectorStore
    from semantic_layer_fvl.writers.vectorstore_writer import VectorStoreWriter

    if pipeline.vectorstore_writer is None:
        pipeline.vectorstore_writer = VectorStoreWriter(settings=pipeline.settings)

    store = pipeline.vectorstore_writer.store
    total_chunks = store.count()

    # Count knowledge files by category
    knowledge_dir = pipeline.settings.resolved_output_dir
    categories: dict[str, int] = {}
    total_files = 0
    if knowledge_dir.exists():
        for md_file in knowledge_dir.rglob("*.md"):
            cat = md_file.parent.name
            categories[cat] = categories.get(cat, 0) + 1
            total_files += 1

    return {
        "total_documents": total_files,
        "total_indexed_chunks": total_chunks,
        "categories": categories,
    }


@router.post("/index")
def index_knowledge() -> dict:
    """Re-indexa todos los archivos Markdown del directorio knowledge/."""
    pipeline = _get_pipeline()
    count = pipeline.index_knowledge_dir()
    return {"indexed": count}
