"""Logging utilities."""

import logging
import sys


def initialize_logging() -> logging.Logger:
    """Initialize logging for the application."""
    lf = logging.Formatter("[%(asctime)s] %(levelname)s[%(module)s] %(message)s")

    sh = logging.StreamHandler(stream=sys.stdout)
    sh.set_name("console")
    sh.setFormatter(lf)
    sh.setLevel(logging.INFO)

    fh = logging.FileHandler(filename="fspachinko.log", mode="w", encoding="utf-8", delay=True)
    fh.set_name("file")
    fh.setFormatter(lf)
    fh.setLevel(logging.DEBUG)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(sh)
    root_logger.addHandler(fh)
    return root_logger
