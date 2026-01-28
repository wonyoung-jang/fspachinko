"""Logging configuration for Mandala."""

import json
import logging.config

from .paths import Paths


def initialize_logging(path: str | None = None) -> None:
    """Initialize logging for the application."""
    if path is None:
        path = Paths.config("logging.json")

    with open(path, encoding="utf-8") as f:
        cfg_dict = json.load(f)
        logging.config.dictConfig(cfg_dict)
