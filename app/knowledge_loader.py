"""Carga el knowledge base desde el JSON generado por el scraper (Fase 1)."""

from __future__ import annotations

import json
from pathlib import Path


def load_knowledge_base(json_path: Path) -> tuple[str, dict]:
    """Lee data/knowledge_base.json y devuelve (contexto_string, stats).

    Returns:
        context: string plano con todos los chunks concatenados, listo para
                 inyección directa en el System Prompt (Context Stuffing).
        stats:   dict con metadatos del knowledge base.
    """
    if not json_path.exists():
        raise FileNotFoundError(
            f"Knowledge base no encontrado en {json_path}. "
            "Ejecuta primero el scraper (Fase 1): python scraper/fvl_scraper.py"
        )

    data = json.loads(json_path.read_text(encoding="utf-8"))

    chunks: list[str] = []
    categories: dict[str, int] = {}

    for item in data:
        source = item.get("metadata", {}).get("source", "desconocido")
        category = item.get("metadata", {}).get("category", "general")
        text = item.get("text", "").strip()

        if not text:
            continue

        categories[category] = categories.get(category, 0) + 1
        chunks.append(f"[Fuente: {source} | Categoría: {category}]\n{text}")

    context = "\n\n---\n\n".join(chunks)
    stats = {
        "total_chunks": len(chunks),
        "categories": categories,
        "estimated_chars": len(context),
        "source_file": str(json_path),
    }
    return context, stats
