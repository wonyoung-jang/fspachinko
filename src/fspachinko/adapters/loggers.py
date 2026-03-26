"""Logging utilities."""

import logging
from os.path import basename, join

from fspachinko.datapaths import get_log_path

logger = logging.getLogger(__name__)


def initialize_logging() -> logging.Logger:
    """Initialize logging for the application."""
    logfile = get_log_path("fspachinko.log")
    fh = logging.FileHandler(filename=logfile, mode="w", encoding="utf-8", delay=True)
    fh.set_name("file")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s[%(module)s] %(message)s"))
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(fh)
    logger.info("Logging initialized. Log file: %s", logfile)
    return root_logger


def add_dest_log_filehandler(dest: str) -> None:
    """Set up a logger for the job request."""
    report_path = join(dest, f"!_{basename(dest)}_report.log")
    handler = logging.FileHandler(report_path, mode="a", encoding="utf-8", delay=True)
    handler.set_name(dest)
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("[%(asctime)s] %(message)s", datefmt="%H:%M:%S"))
    logger.info("Created log handler for destination: %s. Log file: %s", dest, report_path)
    logging.getLogger().addHandler(handler)


def remove_dest_log_filehandler(dest: str) -> None:
    """Remove the log handler for the job request."""
    logger.info("Removing log handler for destination: %s", dest)
    handler = next((h for h in logging.getLogger().handlers if h.get_name() == dest), None)
    if handler:
        logging.getLogger().removeHandler(handler)
        logger.info("Removed log handler for destination: %s", dest)
        handler.close()
    else:
        logger.warning("No log handler found for destination: %s", dest)


def get_cli_log_handler() -> logging.StreamHandler:
    """Get a logging handler for CLI output."""
    handler = logging.StreamHandler()
    handler.set_name("console")
    handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s[%(module)s] %(message)s"))
    handler.setLevel(logging.INFO)
    logger.info("Created CLI log handler.")
    return handler
