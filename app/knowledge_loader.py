"""Carga el knowledge base desde los archivos .md generados por el scraper (Fase 1)."""

from __future__ import annotations

import re
from pathlib import Path


_FRONTMATTER_RE = re.compile(r"^---\n.*?\n---\n?", re.DOTALL)


def load_knowledge_base(knowledge_dir: Path) -> tuple[str, dict]:
    """Lee todos los .md de knowledge/ y devuelve (contexto_string, stats).

    El frontmatter YAML se elimina antes de inyectar al System Prompt.
    Los metadatos del frontmatter alimentan las estadísticas del sidebar.

    Returns:
        context: string listo para Context Stuffing en el System Prompt.
        stats:   compatible con app/main.py:
                   - total_documents (int)
                   - estimated_chars  (int)
                   - categories       (dict[str, list[str]])
                   - source_file      (str)
    """
    if not knowledge_dir.exists():
        raise FileNotFoundError(
            f"Directorio de knowledge base no encontrado: {knowledge_dir}\n"
            "Ejecuta primero el scraper (Fase 1): python scraper/fvl_scraper.py"
        )

    md_files = [f for f in sorted(knowledge_dir.rglob("*.md")) if f.name != ".gitkeep"]

    if not md_files:
        raise FileNotFoundError(
            f"No se encontraron archivos .md en {knowledge_dir}.\n"
            "Ejecuta primero el scraper (Fase 1): python scraper/fvl_scraper.py"
        )

    chunks: list[str] = []
    categories: dict[str, list[str]] = {}

    for md_file in md_files:
        raw = md_file.read_text(encoding="utf-8")

        # Extraer metadatos básicos del frontmatter sin pyyaml
        category = (
            md_file.parent.name
        )  # la carpeta es la categoría (ej. "02_servicios")
        title = md_file.stem  # slug como fallback

        # Buscar title en frontmatter con regex simple
        title_match = re.search(r"^title:\s*[\"']?(.+?)[\"']?\s*$", raw, re.MULTILINE)
        if title_match:
            title = title_match.group(1).strip()

        # Eliminar frontmatter antes de inyectar al contexto
        body = _FRONTMATTER_RE.sub("", raw).strip()
        if not body:
            continue

        categories.setdefault(category, [])
        if title not in categories[category]:
            categories[category].append(title)

        chunks.append(f"[Fuente: {title} | Categoría: {category}]\n{body}")

    context = "\n\n---\n\n".join(chunks)
    stats = {
        "total_documents": len(chunks),
        "categories": categories,
        "estimated_chars": len(context),
        "source_file": str(knowledge_dir),
    }
    return context, stats
