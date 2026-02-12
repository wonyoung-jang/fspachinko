"""Logging configuration."""

import logging.config

from .constants import DefaultPath
from .datapaths import get_config
from .helpers import load_json


def initialize_logging(path: str | None = None) -> None:
    """Initialize logging for the application."""
    if path is None:
        path = get_config(DefaultPath.LOGGING)

    data = load_json(path)
    logging.config.dictConfig(data)
