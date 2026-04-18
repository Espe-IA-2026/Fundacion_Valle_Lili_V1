from __future__ import annotations

from pathlib import Path

from semantic_layer_fvl.config.settings import Settings
from semantic_layer_fvl.schemas import (
    DocumentCategory,
    ExtractionMetadata,
    ProcessedDocument,
    SourceDocument,
)
from semantic_layer_fvl.vectorstore.store import VectorStore
from semantic_layer_fvl.writers.vectorstore_writer import VectorStoreWriter


def test_write_indexes_document(workspace_tmp_path: Path) -> None:
    settings = Settings(chroma_persist_dir=workspace_tmp_path / "chroma", requests_per_second=10)
    store = VectorStore(settings=settings)
    writer = VectorStoreWriter(settings=settings, store=store)

    meta = ExtractionMetadata(
        source_url="https://valledellili.org/test",
        source_name="Test",
        extractor_name="unit-test",
    )
    source = SourceDocument(
        document_id="writer-test",
        title="Test Writer",
        slug="test-writer",
        category=DocumentCategory.SERVICIOS,
        source_url="https://valledellili.org/test",
        source_name="Test",
        extraction_metadata=meta,
    )
    doc = ProcessedDocument(document=source, content_markdown="# Test Writer\n\nContenido de prueba.")

    writer.write(doc)
    assert store.count() >= 1

    results = store.search("prueba")
    assert len(results) >= 1
    assert results[0].parent_document_id == "writer-test"
