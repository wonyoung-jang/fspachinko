"""Main entry point for CLI."""

from ..adapters.loggers import initialize_logging
from ..cli.app import app
from ..cli.loggers_cli import setup_cli_logger


def main() -> None:
    """Enter CLI."""
    initialize_logging()
    setup_cli_logger()
    app()


if __name__ == "__main__":
    main()
