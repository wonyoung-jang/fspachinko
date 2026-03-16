"""Qt logging handler."""

import logging
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QObject, Signal

if TYPE_CHECKING:
    from collections.abc import Callable


def setup_gui_logger(slotfunc: Callable) -> None:
    """Set up the Qt logger."""
    gui_handler = QtLogHandler(slotfunc)
    logging.getLogger().addHandler(gui_handler)


class QtLogHandlerSignals(QObject):
    """Signals for the LogHandler."""

    logged = Signal(str)


class QtLogHandler(logging.Handler):
    """A logging handler that emits log messages to a Qt signal."""

    def __init__(self, slotfunc: Callable, *args: Any, **kwargs: Any) -> None:
        """Initialize the handler and its signals."""
        super().__init__(*args, **kwargs)
        self.signals = QtLogHandlerSignals()
        self.signals.logged.connect(slotfunc)
        self.set_name("qtgui")
        self.setFormatter(logging.Formatter("[%(asctime)s] %(message)s", datefmt="%H:%M:%S"))
        self.setLevel(logging.INFO)

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record by formatting it and emitting the text_written signal."""
        msg = self.format(record)
        self.signals.logged.emit(msg)
