from __future__ import annotations

from typing import Protocol

from semantic_layer_fvl.schemas import ProcessedDocument


class Writer(Protocol):
    """Protocol that all writers must implement."""

    def write(self, document: ProcessedDocument) -> None: ...
