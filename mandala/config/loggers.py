"""Logging configuration for Mandala."""

from __future__ import annotations

import json
import logging.config
from pathlib import Path

LOGGING_CONFIG_PATH = Path(__file__).parent.parent / "logging.json"


def initialize_logging(path: Path | None = None) -> None:
    """Initialize logging for the application."""
    if path is None:
        path = LOGGING_CONFIG_PATH

    with path.open("r", encoding="utf-8") as f:
        logging_config_dict = json.load(f)
        logging.config.dictConfig(logging_config_dict)
