"""Main entry point for CLI."""

import logging

from ..utils import initialize_logging
from .app import app

logger = logging.getLogger(__name__)


def main() -> None:
    """Enter CLI."""
    initialize_logging()
    logger.info("Start: sampledeal CLI")
    app()


if __name__ == "__main__":
    main()
