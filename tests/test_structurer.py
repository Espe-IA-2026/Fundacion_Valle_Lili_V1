from semantic_layer_fvl.processors import SemanticStructurer, slugify
from semantic_layer_fvl.schemas import DocumentCategory, ExtractionMetadata, RawPage


def test_slugify_removes_accents_and_symbols() -> None:
    assert slugify("Cardiologia y Diagnostico!") == "cardiologia-y-diagnostico"


def test_structurer_builds_processed_document_from_raw_page() -> None:
    raw_page = RawPage(
        url="https://valledellili.org/servicios/cardiologia",
        title="Servicio de Cardiologia",
        text_content="Atencion cardiovascular integral.\n\nEquipo especializado.",
        metadata=ExtractionMetadata(
            source_url="https://valledellili.org/servicios/cardiologia",
            source_name="Fundacion Valle del Lili",
            extractor_name="test",
        ),
    )

    processed = SemanticStructurer().build_document(
        raw_page,
        "Atencion cardiovascular integral.\n\nEquipo especializado.",
    )

    assert processed.document.category == DocumentCategory.SERVICIOS
    assert processed.document.slug == "cardiologia"
    assert processed.document.status.value == "ready"
    assert processed.content_markdown.startswith("# Servicio de Cardiologia")


def test_structurer_infers_category_from_redirected_path_segments() -> None:
    raw_page = RawPage(
        url="https://valledellili.org/atencion-al-paciente/especialidades/especialidades/",
        title="Especialidades de la A a la Z",
        text_content="Directorio de especialidades y servicios.",
        metadata=ExtractionMetadata(
            source_url="https://valledellili.org/atencion-al-paciente/especialidades/especialidades/",
            source_name="Fundacion Valle del Lili",
            extractor_name="test",
        ),
    )

    category = SemanticStructurer().infer_category(raw_page, "Directorio de especialidades y servicios.")

    assert category == DocumentCategory.SERVICIOS
