"""Logging configuration for Mandala."""

import json
import logging.config
from typing import TYPE_CHECKING

from .paths import Paths

if TYPE_CHECKING:
    from pathlib import Path


def initialize_logging(path: Path | None = None) -> None:
    """Initialize logging for the application."""
    if path is None:
        path = Paths.config("logging.json")

    with path.open("r", encoding="utf-8") as f:
        cfg_dict = json.load(f)
        logging.config.dictConfig(cfg_dict)
