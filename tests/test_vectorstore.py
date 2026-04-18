from __future__ import annotations

from pathlib import Path

from semantic_layer_fvl.config.settings import Settings
from semantic_layer_fvl.schemas import (
    DocumentCategory,
    ExtractionMetadata,
    ProcessedDocument,
    SearchResult,
    SourceDocument,
)
from semantic_layer_fvl.vectorstore.store import VectorStore


def _make_processed_document(
    doc_id: str,
    title: str,
    content: str,
    category: DocumentCategory = DocumentCategory.SERVICIOS,
) -> ProcessedDocument:
    meta = ExtractionMetadata(
        source_url="https://valledellili.org/test",
        source_name="Test",
        extractor_name="unit-test",
    )
    source = SourceDocument(
        document_id=doc_id,
        title=title,
        slug=doc_id,
        category=category,
        source_url="https://valledellili.org/test",
        source_name="Test",
        extraction_metadata=meta,
    )
    return ProcessedDocument(document=source, content_markdown=content)


def _make_store(tmp_path: Path) -> VectorStore:
    settings = Settings(chroma_persist_dir=tmp_path / "chroma", requests_per_second=10)
    return VectorStore(settings=settings)


def test_upsert_and_search(workspace_tmp_path: Path) -> None:
    store = _make_store(workspace_tmp_path)

    doc = _make_processed_document(
        "test-cardio",
        "Cardiologia",
        "Servicio de cardiologia con atencion cardiovascular integral para adultos y ninos.",
    )
    store.upsert(doc)

    results = store.search("atencion cardiovascular")
    assert len(results) >= 1
    assert results[0].parent_document_id == "test-cardio"
    assert isinstance(results[0], SearchResult)
    assert results[0].distance >= 0


def test_upsert_updates_existing(workspace_tmp_path: Path) -> None:
    store = _make_store(workspace_tmp_path)

    doc_v1 = _make_processed_document("test-update", "Original", "Contenido original del documento.")
    store.upsert(doc_v1)

    doc_v2 = _make_processed_document("test-update", "Actualizado", "Contenido actualizado del documento.")
    store.upsert(doc_v2)

    results = store.search("actualizado")
    assert results[0].title == "Actualizado"


def test_delete_removes_document(workspace_tmp_path: Path) -> None:
    store = _make_store(workspace_tmp_path)

    doc = _make_processed_document("test-delete", "Para Borrar", "Documento temporal para borrar.")
    store.upsert(doc)
    initial_count = store.count()
    assert initial_count >= 1

    store.delete("test-delete")
    assert store.count() == 0


def test_search_returns_ranked_results(workspace_tmp_path: Path) -> None:
    store = _make_store(workspace_tmp_path)

    docs = [
        _make_processed_document(
            "doc-cardio",
            "Cardiologia",
            "Atencion cardiovascular integral con equipo especializado.",
            DocumentCategory.SERVICIOS,
        ),
        _make_processed_document(
            "doc-derma",
            "Dermatologia",
            "Tratamiento de enfermedades de la piel, cabello y unas.",
            DocumentCategory.SERVICIOS,
        ),
        _make_processed_document(
            "doc-neuro",
            "Neurologia",
            "Diagnostico y tratamiento del sistema nervioso central.",
            DocumentCategory.SERVICIOS,
        ),
    ]
    for doc in docs:
        store.upsert(doc)

    results = store.search("corazon cardiovascular", n_results=3)
    assert len(results) == 3
    assert results[0].parent_document_id == "doc-cardio"


def test_reset_clears_all(workspace_tmp_path: Path) -> None:
    store = _make_store(workspace_tmp_path)

    for i in range(3):
        doc = _make_processed_document(f"doc-{i}", f"Documento {i}", f"Contenido del documento {i}.")
        store.upsert(doc)

    assert store.count() >= 3
    store.reset()
    assert store.count() == 0


def test_search_empty_store(workspace_tmp_path: Path) -> None:
    store = _make_store(workspace_tmp_path)
    results = store.search("algo")
    assert results == []


def test_chunked_document_deduplicates_in_search(workspace_tmp_path: Path) -> None:
    """Long document should be chunked but search should return unique parent docs."""
    store = _make_store(workspace_tmp_path)

    paragraphs = [f"Parrafo {i} sobre cardiologia y corazon." for i in range(20)]
    long_content = "\n\n".join(paragraphs)
    doc = _make_processed_document("doc-long", "Documento Largo", long_content)
    store.upsert(doc)

    results = store.search("cardiologia", n_results=5)
    # Even though there are many chunks, only one unique parent should appear
    parent_ids = {r.parent_document_id for r in results}
    assert "doc-long" in parent_ids
    assert len(parent_ids) == 1
