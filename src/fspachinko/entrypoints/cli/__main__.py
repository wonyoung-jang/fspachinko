"""Main entry point for CLI."""

from fspachinko.adapters.loggers import AppLogger

from .app import app


def main() -> None:
    """Enter CLI."""
    logger = AppLogger()
    logger.add_cli_log_handler()
    app()


if __name__ == "__main__":
    main()
