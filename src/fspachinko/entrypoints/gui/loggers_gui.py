"""Qt logging handler."""

import logging
from typing import Any

from PySide6.QtCore import QObject, Signal


class QtLogHandlerSignals(QObject):
    """Signals for the LogHandler."""

    logged = Signal(str)


class QtLogHandler(logging.Handler):
    """A logging handler that emits log messages to a Qt signal."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the handler and its signals."""
        super().__init__(*args, **kwargs)
        self.signals = QtLogHandlerSignals()
        self.set_name("qtgui")
        self.setFormatter(logging.Formatter("[%(asctime)s] %(message)s", datefmt="%H:%M:%S"))
        self.setLevel(logging.INFO)

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record by formatting it and emitting the text_written signal."""
        msg = self.format(record)
        self.signals.logged.emit(msg)
