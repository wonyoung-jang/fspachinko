"""Main entry point for CLI."""

from ..adapters import initialize_logging
from .app import app
from .loggers_cli import setup_cli_logger


def main() -> None:
    """Enter CLI."""
    initialize_logging()
    setup_cli_logger()
    app()


if __name__ == "__main__":
    main()
