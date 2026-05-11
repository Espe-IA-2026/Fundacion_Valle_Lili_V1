"""Tests unitarios offline para rag.indexer.KnowledgeIndexer."""

from __future__ import annotations

import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ── Fixture compartido: settings falso ────────────────────────────────────────

@pytest.fixture()
def mock_settings(tmp_path: Path) -> MagicMock:
    """Settings mock con rutas apuntando a directorios temporales."""
    settings = MagicMock()
    settings.resolved_knowledge_dir = tmp_path / "knowledge"
    settings.resolved_chroma_persist_dir = tmp_path / "chroma_db"
    settings.embedding_model = "text-embedding-3-small"
    return settings


# ── Fixture: directorio knowledge con archivos .md de prueba ──────────────────

@pytest.fixture()
def sample_knowledge_dir(tmp_path: Path) -> Path:
    """Crea un directorio knowledge mínimo con un archivo .md de prueba."""
    content = textwrap.dedent("""\
        ---
        title: Cardiología
        category: 01_servicios
        slug: cardiologia
        source_url: https://valledellili.org/cardiologia
        source_type: web
        ---

        # Cardiología

        La FVL ofrece atención cardiovascular integral de alta complejidad.
        Diagnóstico y tratamiento de enfermedades del corazón y sistema vascular.
    """)
    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    servicios = knowledge / "01_servicios"
    servicios.mkdir()
    (servicios / "cardiologia.md").write_text(content, encoding="utf-8")
    return knowledge


# ── Fixture: indexer con dependencias mockeadas ────────────────────────────────

@pytest.fixture()
def indexer(mock_settings: MagicMock):
    """KnowledgeIndexer con get_settings y OpenAIEmbeddings mockeados."""
    with patch("rag.indexer.get_settings", return_value=mock_settings), \
         patch("rag.indexer.OpenAIEmbeddings", return_value=MagicMock()):
        from rag.indexer import KnowledgeIndexer
        return KnowledgeIndexer()


# ── Tests de _parse_frontmatter ───────────────────────────────────────────────

def test_parse_frontmatter_valid(indexer) -> None:
    """_parse_frontmatter extrae correctamente un bloque YAML bien formado."""
    raw = "---\ntitle: Cardiología\ncategory: 01_servicios\nslug: cardiologia\n---\n# Contenido"

    result = indexer._parse_frontmatter(raw)

    assert result["title"] == "Cardiología"
    assert result["category"] == "01_servicios"
    assert result["slug"] == "cardiologia"


def test_parse_frontmatter_invalid_yaml(indexer) -> None:
    """_parse_frontmatter devuelve dict vacío cuando el YAML está malformado."""
    raw = "---\n: clave_sin_valor: [\n---\n# Contenido"

    result = indexer._parse_frontmatter(raw)

    assert result == {}


def test_parse_frontmatter_missing(indexer) -> None:
    """_parse_frontmatter devuelve dict vacío cuando no existe bloque ---."""
    raw = "# Solo contenido sin frontmatter"

    result = indexer._parse_frontmatter(raw)

    assert result == {}


# ── Tests de _index_exists ────────────────────────────────────────────────────

def test_index_exists_returns_false_when_no_sqlite(indexer, tmp_path: Path) -> None:
    """_index_exists retorna False cuando chroma.sqlite3 no existe."""
    # tmp_path está vacío → no hay base vectorial previa
    assert not indexer._index_exists()


def test_index_exists_returns_true_when_sqlite_present(
    mock_settings: MagicMock, tmp_path: Path
) -> None:
    """_index_exists retorna True cuando chroma.sqlite3 existe en el directorio."""
    chroma_dir = tmp_path / "chroma_db"
    chroma_dir.mkdir()
    (chroma_dir / "chroma.sqlite3").touch()
    mock_settings.resolved_chroma_persist_dir = chroma_dir

    with patch("rag.indexer.get_settings", return_value=mock_settings), \
         patch("rag.indexer.OpenAIEmbeddings", return_value=MagicMock()):
        from rag.indexer import KnowledgeIndexer
        indexer = KnowledgeIndexer()

    assert indexer._index_exists()


# ── Tests de _load_documents ──────────────────────────────────────────────────

def test_load_documents_raises_when_no_md_files(
    mock_settings: MagicMock, tmp_path: Path
) -> None:
    """_load_documents lanza ValueError si no hay archivos .md en knowledge_dir."""
    empty_dir = tmp_path / "knowledge"
    empty_dir.mkdir()
    mock_settings.resolved_knowledge_dir = empty_dir

    with patch("rag.indexer.get_settings", return_value=mock_settings), \
         patch("rag.indexer.OpenAIEmbeddings", return_value=MagicMock()):
        from rag.indexer import KnowledgeIndexer
        indexer = KnowledgeIndexer()

    with pytest.raises(ValueError, match="No hay archivos .md"):
        indexer._load_documents()


def test_load_documents_creates_chunks_with_metadata(
    mock_settings: MagicMock, sample_knowledge_dir: Path
) -> None:
    """_load_documents genera Documents con metadatos del frontmatter y chunk_index."""
    mock_settings.resolved_knowledge_dir = sample_knowledge_dir

    with patch("rag.indexer.get_settings", return_value=mock_settings), \
         patch("rag.indexer.OpenAIEmbeddings", return_value=MagicMock()):
        from rag.indexer import KnowledgeIndexer
        indexer = KnowledgeIndexer()

    docs = indexer._load_documents()

    assert len(docs) >= 1
    assert docs[0].page_content.strip() != ""
    assert "chunk_index" in docs[0].metadata
    assert "source_file" in docs[0].metadata
    assert docs[0].metadata["title"] == "Cardiología"


# ── Tests de build_or_load ────────────────────────────────────────────────────

def test_build_or_load_loads_existing_index(
    mock_settings: MagicMock, tmp_path: Path
) -> None:
    """build_or_load llama a Chroma() para carga cuando el índice ya existe."""
    chroma_dir = tmp_path / "chroma_db"
    chroma_dir.mkdir()
    (chroma_dir / "chroma.sqlite3").touch()
    mock_settings.resolved_chroma_persist_dir = chroma_dir

    with patch("rag.indexer.get_settings", return_value=mock_settings), \
         patch("rag.indexer.OpenAIEmbeddings", return_value=MagicMock()), \
         patch("rag.indexer.Chroma") as mock_chroma:
        mock_chroma.return_value = MagicMock()
        from rag.indexer import KnowledgeIndexer
        indexer = KnowledgeIndexer()
        indexer.build_or_load()

    mock_chroma.assert_called_once()
    mock_chroma.from_documents.assert_not_called()


# ── Tests de _drop_collection ─────────────────────────────────────────────────

def test_drop_collection_removes_chroma_dir(
    mock_settings: MagicMock, tmp_path: Path
) -> None:
    """_drop_collection elimina el directorio ChromaDB cuando existe."""
    chroma_dir = tmp_path / "chroma_db"
    chroma_dir.mkdir()
    (chroma_dir / "chroma.sqlite3").touch()
    mock_settings.resolved_chroma_persist_dir = chroma_dir

    with patch("rag.indexer.get_settings", return_value=mock_settings), \
         patch("rag.indexer.OpenAIEmbeddings", return_value=MagicMock()):
        from rag.indexer import KnowledgeIndexer
        indexer = KnowledgeIndexer()

    indexer._drop_collection()

    assert not chroma_dir.exists()