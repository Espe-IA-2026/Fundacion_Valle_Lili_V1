from semantic_layer_fvl.schemas import (
    DocumentCategory,
    ExtractionMetadata,
    ProcessedDocument,
    SourceDocument,
)


def test_processed_document_keeps_nested_document_metadata() -> None:
    metadata = ExtractionMetadata(
        source_url="https://valledellili.org/servicios",
        source_name="Fundacion Valle del Lili",
        extractor_name="unit-test",
    )
    document = SourceDocument(
        document_id="servicios-cardiologia",
        title="Cardiologia",
        slug="cardiologia",
        category=DocumentCategory.SERVICIOS,
        source_url="https://valledellili.org/servicios/cardiologia",
        source_name="Fundacion Valle del Lili",
        extraction_metadata=metadata,
    )

    processed = ProcessedDocument(document=document, content_markdown="# Cardiologia")

    assert processed.document.category == DocumentCategory.SERVICIOS
    assert processed.content_markdown.startswith("#")
