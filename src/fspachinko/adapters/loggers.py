"""Logging utilities."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from os.path import basename, join

from .datapaths import get_log_path


def initialize_logging() -> logging.Logger:
    """Initialize logging for the application."""
    logfile = get_log_path("fspachinko.log")
    fh = logging.FileHandler(filename=logfile, mode="w", encoding="utf-8", delay=True)
    fh.set_name("file")
    fh.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s[%(module)s] %(message)s"))
    fh.setLevel(logging.DEBUG)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(fh)
    return root_logger


def get_dest_log_filehandler(dest: str) -> logging.FileHandler:
    """Set up a logger for the job request."""
    report_path = join(dest, f"!_{basename(dest)}_report.log")
    handler = logging.FileHandler(report_path, mode="a", encoding="utf-8", delay=True)
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("[%(asctime)s] %(message)s", datefmt="%H:%M:%S"))
    return handler


@dataclass(slots=True)
class AbstractLoggingPort(ABC):
    """Abstract port for logging operations."""

    @abstractmethod
    def add_handler(self, dest: str) -> None:
        """Add a logging handler."""

    @abstractmethod
    def remove_handler(self) -> None:
        """Remove a logging handler."""


@dataclass(slots=True)
class ConcreteLoggingPort(AbstractLoggingPort):
    """Adapter for logging operations."""

    handler: logging.FileHandler | None = None

    def add_handler(self, dest: str) -> None:
        """Add a logging handler."""
        self.handler = get_dest_log_filehandler(dest)
        logging.getLogger().addHandler(self.handler)

    def remove_handler(self) -> None:
        """Remove the logging handler."""
        if self.handler:
            logging.getLogger().removeHandler(self.handler)
            self.handler.close()
            self.handler = None
