from __future__ import annotations

from pathlib import Path


def load_knowledge_base(knowledge_dir: Path) -> tuple[str, dict]:
    """Load all .md files from the knowledge directory and return consolidated context + stats.

    Returns:
        context: single string with all document contents separated by dividers.
        stats: dict with total_documents count and per-category document names.
    """
    files = sorted(knowledge_dir.rglob("*.md"))
    files = [f for f in files if f.name != ".gitkeep"]

    categories: dict[str, list[str]] = {}
    chunks: list[str] = []

    for file in files:
        category = file.parent.name
        categories.setdefault(category, []).append(file.stem)
        content = file.read_text(encoding="utf-8").strip()
        chunks.append(f"### [{category}] {file.stem}\n\n{content}")

    context = "\n\n---\n\n".join(chunks)
    stats = {
        "total_documents": len(files),
        "categories": categories,
        "estimated_chars": len(context),
    }
    return context, stats
