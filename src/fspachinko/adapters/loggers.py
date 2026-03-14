"""Logging utilities."""

import logging
from os.path import basename, join

from .filesystemport import get_log_path


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
    return root_logger


def get_dest_log_filehandler(dest: str) -> logging.FileHandler:
    """Set up a logger for the job request."""
    report_path = join(dest, f"!_{basename(dest)}_report.log")
    handler = logging.FileHandler(report_path, mode="a", encoding="utf-8", delay=True)
    handler.set_name(dest)
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("[%(asctime)s] %(message)s", datefmt="%H:%M:%S"))
    return handler
