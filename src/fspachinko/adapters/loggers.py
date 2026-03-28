"""Logging utilities."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from os.path import basename, join
from typing import Any

from fspachinko.datapaths import get_log_path

logger = logging.getLogger(__name__)


class AbstractLogger(ABC):
    """Abstract base class for loggers."""

    @abstractmethod
    def add_handler(self, name: str, handler: logging.Handler) -> None:
        """Add a logging handler."""

    @abstractmethod
    def add_cli_log_handler(self) -> None:
        """Get a logging handler for CLI output."""

    @abstractmethod
    def add_dest_log_filehandler(self, dest: str) -> None:
        """Set up a logger for the job request."""

    @abstractmethod
    def remove_dest_log_filehandler(self, dest: str) -> None:
        """Remove the log handler for the job request."""

    @abstractmethod
    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log an info message."""

    @abstractmethod
    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a warning message."""


@dataclass(slots=True)
class AppLogger(AbstractLogger):
    """Logger implementation."""

    logger: logging.Logger = field(init=False)
    handlers: dict[str, logging.Handler] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Initialize the root logger."""
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.DEBUG)
        self.add_file_log_handler()

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a debug message."""
        self.logger.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log an info message."""
        self.logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a warning message."""
        self.logger.warning(msg, *args, **kwargs)

    def add_handler(self, name: str, handler: logging.Handler) -> None:
        """Add a logging handler."""
        self.handlers[name] = handler
        self.logger.addHandler(handler)

    def add_file_log_handler(self) -> None:
        """Add a file log handler."""
        logfile = get_log_path("fspachinko.log")
        handler = logging.FileHandler(filename=logfile, mode="a", encoding="utf-8", delay=True)
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s[%(module)s] %(message)s"))
        self.add_handler("file", handler)
        self.debug("Added file log handler. Log file: %s", logfile)

    def add_cli_log_handler(self) -> None:
        """Get a logging handler for CLI output."""
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s[%(module)s] %(message)s"))
        handler.setLevel(logging.INFO)
        self.add_handler("console", handler)
        self.debug("Created CLI log handler.")

    def add_dest_log_filehandler(self, dest: str) -> None:
        """Set up a logger for the job request."""
        report_path = join(dest, f"!_{basename(dest)}_report.log")
        handler = logging.FileHandler(report_path, mode="a", encoding="utf-8", delay=True)
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter("[%(asctime)s] %(message)s", datefmt="%H:%M:%S"))
        self.add_handler(dest, handler)
        self.debug("Created log handler for destination: %s. Log file: %s", dest, report_path)

    def remove_dest_log_filehandler(self, dest: str) -> None:
        """Remove the log handler for the job request."""
        self.debug("Removing log handler for destination: %s", dest)
        handler = self.handlers.pop(dest, None)
        if handler:
            self.logger.removeHandler(handler)
            self.debug("Removed log handler for destination: %s", dest)
            handler.close()
        else:
            self.warning("No log handler found for destination: %s", dest)
