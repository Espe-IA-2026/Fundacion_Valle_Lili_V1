"""Carga el knowledge base desde el JSON generado por el scraper (Fase 1)."""

from __future__ import annotations

import json
from pathlib import Path


def load_knowledge_base(json_path: Path) -> tuple[str, dict]:
    """Lee data/knowledge_base.json y devuelve (contexto_string, stats).

    El JSON debe ser una lista de objetos:
        [{"text": "...", "metadata": {"source": "...", "category": "..."}}, ...]

    Returns:
        context: string listo para inyección directa en el System Prompt.
        stats:   compatible con app/main.py:
                   - total_documents (int)
                   - estimated_chars  (int)
                   - categories       (dict[str, list[str]])
                   - source_file      (str)
    """
    if not json_path.exists():
        raise FileNotFoundError(
            f"Knowledge base no encontrado en {json_path}.\n"
            "Ejecuta primero el scraper (Fase 1): python scraper/fvl_scraper.py"
        )

    data = json.loads(json_path.read_text(encoding="utf-8"))

    chunks: list[str] = []
    categories: dict[str, list[str]] = {}

    for item in data:
        meta = item.get("metadata", {})
        source = meta.get("source", "desconocido")
        category = meta.get("category", "general")
        text = item.get("text", "").strip()

        if not text:
            continue

        categories.setdefault(category, [])
        title = meta.get("title", source)
        if title not in categories[category]:
            categories[category].append(title)

        chunks.append(f"[Fuente: {source} | Categoría: {category}]\n{text}")

    context = "\n\n---\n\n".join(chunks)
    stats = {
        "total_documents": len(chunks),
        "categories": categories,
        "estimated_chars": len(context),
        "source_file": str(json_path),
    }
    return context, stats
