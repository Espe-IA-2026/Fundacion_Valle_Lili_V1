from __future__ import annotations

from pathlib import Path

from semantic_layer_fvl.config import Settings, get_settings
from semantic_layer_fvl.schemas import ProcessedDocument


class MarkdownWriter:
    """Renders processed documents to Markdown files with YAML frontmatter."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def resolve_output_path(
        self,
        document: ProcessedDocument,
        domain_folder: str | None = None,
    ) -> Path:
        folder = domain_folder or document.document.category.value
        return (
            self.settings.resolved_output_dir / folder / f"{document.document.slug}.md"
        )

    def write(
        self,
        document: ProcessedDocument,
        domain_folder: str | None = None,
    ) -> Path:
        output_path = self.resolve_output_path(document, domain_folder=domain_folder)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            self.render(document, domain_folder=domain_folder), encoding="utf-8"
        )
        return output_path

    def render(
        self,
        document: ProcessedDocument,
        domain_folder: str | None = None,
    ) -> str:
        frontmatter = self._build_frontmatter(document, domain_folder=domain_folder)
        body = document.content_markdown.strip()
        return f"---\n{frontmatter}\n---\n\n{body}\n"

    @staticmethod
    def _build_frontmatter(
        document: ProcessedDocument,
        domain_folder: str | None = None,
    ) -> str:
        doc = document.document
        meta = doc.extraction_metadata
        lines = [
            f'domain: "{MarkdownWriter._escape(domain_folder or doc.category.value)}"',
            f'title: "{MarkdownWriter._escape(doc.title)}"',
            f'document_id: "{MarkdownWriter._escape(doc.document_id)}"',
            f'category: "{doc.category.value}"',
            f'slug: "{MarkdownWriter._escape(doc.slug)}"',
            f'source_url: "{doc.source_url}"',
            f'source_name: "{MarkdownWriter._escape(doc.source_name)}"',
            f'status: "{doc.status.value}"',
            f'extraction_date: "{meta.extracted_at.date().isoformat()}"',
            f'extracted_at: "{meta.extracted_at.isoformat()}"',
            f'extractor_name: "{MarkdownWriter._escape(meta.extractor_name)}"',
        ]

        if doc.summary:
            lines.append(f'summary: "{MarkdownWriter._escape(doc.summary)}"')

        if meta.http_status is not None:
            lines.append(f"http_status: {meta.http_status}")

        if meta.content_type:
            lines.append(f'content_type: "{MarkdownWriter._escape(meta.content_type)}"')

        if doc.tags:
            lines.append("tags:")
            for tag in doc.tags:
                lines.append(f'  - "{MarkdownWriter._escape(tag)}"')
        else:
            lines.append("tags: []")

        for key, value in document.extra_metadata.items():
            lines.append(f'{key}: "{MarkdownWriter._escape(value)}"')

        if document.warnings:
            lines.append("warnings:")
            for warning in document.warnings:
                lines.append(f'  - "{MarkdownWriter._escape(warning)}"')
        else:
            lines.append("warnings: []")

        return "\n".join(lines)

    @staticmethod
    def _escape(value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')
