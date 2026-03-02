"""Main entry point for CLI."""

import logging

from ..adapters import initialize_logging
from .app import app
from .loggers import setup_cli_logger

logger = logging.getLogger(__name__)


def main() -> None:
    """Enter CLI."""
    initialize_logging()
    setup_cli_logger()
    app()


if __name__ == "__main__":
    main()
