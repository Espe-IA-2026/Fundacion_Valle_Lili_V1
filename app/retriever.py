from __future__ import annotations

from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

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
        n = min(k, self._col.count())
        results = self._col.query(query_texts=[query], n_results=n)
        return "\n\n---\n\n".join(results["documents"][0])

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
            categories.setdefault(cat, []).append(meta["name"])
        return {
            "total_documents": self._col.count(),
            "categories": {k: sorted(v) for k, v in sorted(categories.items())},
            "estimated_chars": sum(len(d) for d in self._col.get(include=["documents"])["documents"]),
        }


def build_retriever(knowledge_dir: Path, persist_dir: Path) -> Retriever:
    ef = SentenceTransformerEmbeddingFunction(model_name=_EMBED_MODEL)
    client = chromadb.PersistentClient(path=str(persist_dir))
    collection = client.get_or_create_collection(_COLLECTION, embedding_function=ef)

    if collection.count() == 0:
        _index_documents(collection, knowledge_dir)

    return Retriever(collection)


def _index_documents(collection: chromadb.Collection, knowledge_dir: Path) -> None:
    files = sorted(f for f in knowledge_dir.rglob("*.md") if f.name != ".gitkeep")
    docs, ids, metas = [], [], []
    for file in files:
        category = file.parent.name
        doc_id = f"{category}/{file.stem}"
        content = file.read_text(encoding="utf-8").strip()
        docs.append(f"### [{category}] {file.stem}\n\n{content}")
        ids.append(doc_id)
        metas.append({"category": category, "name": file.stem})

    batch = 50
    for i in range(0, len(docs), batch):
        collection.add(documents=docs[i : i + batch], ids=ids[i : i + batch], metadatas=metas[i : i + batch])
