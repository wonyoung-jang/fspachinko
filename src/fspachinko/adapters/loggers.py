"""Logging utilities."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from os.path import basename, join
from typing import TYPE_CHECKING, Any

from fspachinko.datapaths import get_log_path
from fspachinko.fp import Fp

if TYPE_CHECKING:
    from collections.abc import Callable


class AbstractLogger(ABC):
    """Abstract base class for loggers."""

    @abstractmethod
    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a debug message."""

    @abstractmethod
    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log an info message."""

    @abstractmethod
    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a warning message."""

    @abstractmethod
    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log an exception message."""

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


@dataclass(slots=True)
class AppLogger(AbstractLogger):
    """Logger implementation."""

    _logger: logging.Logger = field(init=False)
    _handlers: dict[str, logging.Handler] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize the root logger."""
        self._logger = logging.getLogger(Fp.LogData.NAME)
        self._logger.setLevel(logging.DEBUG)
        self.add_global_file_log_handler()
        self.debug("Initialized AppLogger with file log handler.")

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a debug message."""
        self._logger.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log an info message."""
        self._logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a warning message."""
        self._logger.warning(msg, *args, **kwargs)

    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log an exception message."""
        self._logger.exception(msg, *args, **kwargs)

    def add_handler(self, name: str, handler: logging.Handler) -> None:
        """Add a logging handler."""
        if name in self._handlers:
            self.warning("Handler '%s' already registered. Skipping addition.", name)
            return
        self._handlers[name] = handler
        self._logger.addHandler(handler)

    def add_global_file_log_handler(self) -> None:
        """Add a file log handler."""
        filename = get_log_path(Fp.Path.LOG_FILE)
        handler = logging.FileHandler(
            filename=filename,
            mode="w",
            encoding="utf-8",
            delay=True,
        )
        handler.setFormatter(logging.Formatter(Fp.LogFmt.DEFAULT))
        handler.setLevel(logging.DEBUG)
        self.add_handler("file", handler)
        self.debug("Added file log handler. Log file: %s", filename)

    def add_cli_log_handler(self) -> None:
        """Get a logging handler for CLI output."""
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(Fp.LogFmt.DEFAULT))
        handler.setLevel(logging.INFO)
        self.add_handler("console", handler)
        self.debug("Created CLI log handler.")

    def add_dest_log_filehandler(self, dest: str) -> None:
        """Set up a logger for the job request."""
        filename = join(dest, f"!_{basename(dest)}_report.log")
        handler = logging.FileHandler(
            filename=filename,
            mode="a",
            encoding="utf-8",
            delay=True,
        )
        handler.setFormatter(logging.Formatter(Fp.LogFmt.DEST, datefmt=Fp.LogDateFmt.HHMMSS))
        handler.setLevel(logging.INFO)
        self.add_handler(dest, handler)
        self.debug("Created log handler for destination %s logging to file: %s", dest, filename)

    def remove_dest_log_filehandler(self, dest: str) -> None:
        """Remove the log handler for the job request."""
        if handler := self._handlers.pop(dest, None):
            self._logger.removeHandler(handler)
            self.debug("Removed log handler for destination: %s", dest)
            handler.close()
        else:
            self.warning("No log handler found for destination: %s", dest)


class AttachedLogHandler(logging.Handler):
    """A logging handler that emits log messages to a provided callable, such as a GUI log widget."""

    def __init__(self, call: Callable[[str], None]) -> None:
        """Initialize the handler."""
        super().__init__()
        self.call = call
        self.setFormatter(logging.Formatter(Fp.LogFmt.DEST, datefmt=Fp.LogDateFmt.HHMMSS))
        self.setLevel(logging.INFO)

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record by formatting it and calling the provided function."""
        self.call(self.format(record))
