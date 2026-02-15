"""Main entry point for CLI."""

import logging

from ..core import initialize_logging
from .app import app

logger = logging.getLogger(__name__)


def main() -> None:
    """Enter CLI."""
    initialize_logging()
    app()


if __name__ == "__main__":
    main()
