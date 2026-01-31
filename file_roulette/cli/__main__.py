"""Main entry point for File Roulette CLI."""

import logging

from ..utils import initialize_logging
from .app import app

logger = logging.getLogger(__name__)


def main() -> None:
    """Enter File Roulette CLI."""
    initialize_logging()
    logger.info("Start: File Roulette GUI")
    app()


if __name__ == "__main__":
    main()
