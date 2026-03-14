"""Main entry point for CLI."""

import logging

from ..adapters.loggers import get_cli_log_handler, initialize_logging
from ..cli.app import app


def main() -> None:
    """Enter CLI."""
    initialize_logging()
    cli_loghandler = get_cli_log_handler()
    logging.getLogger().addHandler(cli_loghandler)
    app()


if __name__ == "__main__":
    main()
