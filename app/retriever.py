from __future__ import annotations

import sys
from pathlib import Path

import chromadb

# Ensure the project source is importable
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from semantic_layer_fvl.vectorstore.embeddings import EmbeddingService  # noqa: E402

_EMBED_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
_COLLECTION = "fvl_knowledge"

_BROAD_QUERIES = [
    "misión visión valores historia fundación",
    "servicios médicos especialidades atención pacientes",
    "contacto sedes ubicaciones teléfonos dirección",
    "investigación clínica ensayos educación formación",
    "normatividad certificaciones calidad acreditación",
    "noticias eventos novedades programas",
]


class Retriever:
    def __init__(self, collection: chromadb.Collection) -> None:
        self._col = collection

    @property
    def count(self) -> int:
        return self._col.count()

    def retrieve(self, query: str, k: int = 8) -> str:
        # Heurística de Query Expansion para asegurar que preguntas clave recuperen la info correcta
        queries = []
        q_low = query.lower()
        if "valor" in q_low:
            queries.append("valores institucionales")
        if "misión" in q_low or "mision" in q_low:
            queries.append("misión institucional")
        if "visión" in q_low or "vision" in q_low:
            queries.append("visión institucional")
        if "historia" in q_low:
            queries.append("historia institucional")
            
        queries.append(query)
        n = min(k, self._col.count())
        results = self._col.query(query_texts=queries, n_results=n)
        
        seen = set()
        docs = []
        for doc_list, id_list in zip(results["documents"], results["ids"]):
            for doc, doc_id in zip(doc_list, id_list):
                if doc_id not in seen:
                    seen.add(doc_id)
                    docs.append(doc)
                    
        return "\n\n---\n\n".join(docs[:k])

    def retrieve_broad(self, k: int = 50) -> str:
        """Multi-query retrieval for broad topic coverage (summary / FAQ)."""
        per_query = max(k // len(_BROAD_QUERIES), 3)
        seen: set[str] = set()
        docs: list[str] = []
        for query in _BROAD_QUERIES:
            n = min(per_query, self._col.count())
            results = self._col.query(query_texts=[query], n_results=n)
            for doc_id, doc in zip(results["ids"][0], results["documents"][0]):
                if doc_id not in seen:
                    seen.add(doc_id)
                    docs.append(doc)
        return "\n\n---\n\n".join(docs[:k])

    def stats(self) -> dict:
        result = self._col.get(include=["metadatas"])
        categories: dict[str, list[str]] = {}
        for meta in result["metadatas"]:
            cat = meta["category"]
            title = meta.get("title", meta.get("name", "unknown"))
            categories.setdefault(cat, []).append(title)
        # Deduplicate titles within each category
        return {
            "total_documents": self._col.count(),
            "categories": {k: sorted(set(v)) for k, v in sorted(categories.items())},
            "estimated_chars": sum(len(d) for d in self._col.get(include=["documents"])["documents"]),
        }


def build_retriever(knowledge_dir: Path, persist_dir: Path) -> Retriever:
    ef = EmbeddingService(model_name=_EMBED_MODEL)
    client = chromadb.PersistentClient(path=str(persist_dir))
    collection = client.get_or_create_collection(_COLLECTION, embedding_function=ef)

    if collection.count() == 0:
        _index_documents(collection, knowledge_dir)

    return Retriever(collection)


def _strip_frontmatter(content: str) -> str:
    """Remove YAML front-matter from markdown content."""
    import re
    match = re.match(r"^---\r?\n(.+?)\r?\n---\r?\n\n?(.*)", content, re.DOTALL)
    if match:
        return match.group(2).strip()
    return content


def _index_documents(collection: chromadb.Collection, knowledge_dir: Path) -> None:
    from semantic_layer_fvl.processors.chunker import TextChunker

    chunker = TextChunker(max_chunk_size=1500, chunk_overlap=300)
    files = sorted(f for f in knowledge_dir.rglob("*.md") if f.name != ".gitkeep")
    docs, ids, metas = [], [], []

    for file in files:
        category = file.parent.name
        raw_content = file.read_text(encoding="utf-8").strip()
        body = _strip_frontmatter(raw_content)

        if not body:
            continue

        chunks = chunker.chunk(body)
        if not chunks:
            chunks = [body]

        for i, chunk_text in enumerate(chunks):
            chunk_id = f"{category}/{file.stem}::chunk-{i}"
            # Prepend context to EVERY chunk so it retains semantic meaning
            enriched_chunk = f"### [{category}] {file.stem}\n\n{chunk_text}"
            docs.append(enriched_chunk)
            ids.append(chunk_id)
            metas.append({
                "category": category,
                "name": file.stem,
                "title": file.stem,
                "chunk_index": i,
                "total_chunks": len(chunks),
            })

    batch = 50
    for i in range(0, len(docs), batch):
        collection.add(
            documents=docs[i : i + batch],
            ids=ids[i : i + batch],
            metadatas=metas[i : i + batch],
        )

