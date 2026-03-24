"""Workers for GUI."""

import logging

from PySide6.QtCore import QObject, QThreadPool, Signal

root_logger = logging.getLogger()


class WorkerSignals(QObject):
    """Qt worker signals."""

    process_started = Signal()
    finished = Signal()
    stopped = Signal()


class ProcessController(QObject):
    """Qt worker signals."""

    def __init__(self) -> None:
        """Initialize the process controller."""
        super().__init__()
        self.signals = WorkerSignals()
        self.threadpool = QThreadPool()

    def start(self) -> None:
        """Start the process."""
        self.threadpool.start(self.run)

    def run(self) -> None:
        """Run the process."""
        self.signals.process_started.emit()
        self.signals.finished.emit()

    def stop(self) -> None:
        """Stop the process."""
        self.signals.stopped.emit()
