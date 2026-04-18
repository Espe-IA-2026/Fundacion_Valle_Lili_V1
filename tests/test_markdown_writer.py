from pathlib import Path

from semantic_layer_fvl.config.settings import Settings
from semantic_layer_fvl.schemas import DocumentCategory, ExtractionMetadata, ProcessedDocument, SourceDocument
from semantic_layer_fvl.writers import MarkdownWriter


def build_processed_document() -> ProcessedDocument:
    metadata = ExtractionMetadata(
        source_url="https://valledellili.org/servicios/cardiologia",
        source_name="Fundacion Valle del Lili",
        extractor_name="test-writer",
        http_status=200,
        content_type="text/html",
    )
    source = SourceDocument(
        document_id="02_servicios-cardiologia",
        title="Servicio de Cardiologia",
        slug="cardiologia",
        category=DocumentCategory.SERVICIOS,
        source_url="https://valledellili.org/servicios/cardiologia",
        source_name="Fundacion Valle del Lili",
        summary="Atencion cardiovascular integral.",
        extraction_metadata=metadata,
    )
    return ProcessedDocument(document=source, content_markdown="# Servicio de Cardiologia")


def test_markdown_writer_renders_frontmatter() -> None:
    rendered = MarkdownWriter(Settings()).render(build_processed_document())

    assert rendered.startswith("---\n")
    assert 'title: "Servicio de Cardiologia"' in rendered
    assert "# Servicio de Cardiologia" in rendered


def test_markdown_writer_resolves_document_path_by_category(workspace_tmp_path: Path) -> None:
    settings = Settings(output_dir=workspace_tmp_path)
    writer = MarkdownWriter(settings)

    output_path = writer.resolve_output_path(build_processed_document())

    assert output_path == workspace_tmp_path / "02_servicios" / "cardiologia.md"
