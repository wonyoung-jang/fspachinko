"""Loggers for CLI."""

import logging


def setup_cli_logger() -> None:
    """Set up the CLI logger."""
    logging.getLogger().addHandler(get_cli_log_handler())


def get_cli_log_handler() -> logging.Handler:
    """Get a logging handler for CLI output."""
    handler = logging.StreamHandler()
    handler.set_name("console")
    handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s[%(module)s] %(message)s"))
    handler.setLevel(logging.INFO)
    return handler
