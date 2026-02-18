"""Qt logging handler."""

import logging
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QObject, Signal

if TYPE_CHECKING:
    from collections.abc import Callable


def setup_gui_logger(slotfunc: Callable) -> None:
    """Set up the Qt logger."""
    qt_log_handler = QtLogHandler(slotfunc)
    logging.getLogger().addHandler(qt_log_handler)


class QtLogHandlerSignals(QObject):
    """Signals for the LogHandler."""

    on_log = Signal(str)


class QtLogHandler(logging.Handler):
    """A logging handler that emits log messages to a Qt signal."""

    def __init__(self, slotfunc: Callable, *args: Any, **kwargs: Any) -> None:
        """Initialize the handler and its signals."""
        super().__init__(*args, **kwargs)
        self.signals = QtLogHandlerSignals()
        self.signals.on_log.connect(slotfunc)
        self.set_name("qtgui")
        self.setFormatter(logging.Formatter("[%(asctime)s] %(message)s", datefmt="%H:%M:%S"))
        self.setLevel(logging.INFO)

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record by formatting it and emitting the text_written signal."""
        msg = self.format(record)
        self.signals.on_log.emit(msg)
