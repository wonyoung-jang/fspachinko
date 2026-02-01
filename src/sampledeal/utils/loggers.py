"""Logging configuration."""

import logging.config

from .constants import DefaultPath
from .helpers import load_json
from .paths import Paths


def initialize_logging(path: str | None = None) -> None:
    """Initialize logging for the application."""
    if path is None:
        path = Paths.config(DefaultPath.LOGGING)

    data = load_json(path)
    logging.config.dictConfig(data)
