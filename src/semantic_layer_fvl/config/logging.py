from __future__ import annotations

import logging

from semantic_layer_fvl.config.settings import Settings, get_settings


def configure_logging(settings: Settings | None = None) -> None:
    current_settings = settings or get_settings()
    logging.basicConfig(
        level=getattr(logging, current_settings.log_level),
        format="%(levelname)s %(name)s: %(message)s",
        force=True,
    )
