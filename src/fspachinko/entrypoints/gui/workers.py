"""Workers for GUI."""

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

if TYPE_CHECKING:
    from fspachinko.bootstrap import MessageBus
    from fspachinko.domain.commands import Command


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
        self.worker = None

    def on_start(self, bus: MessageBus, cmd: Command) -> None:
        """Start the process."""
        self.worker = ProcessWorker(self.signals, bus, cmd)
        self.threadpool.tryStart(self.worker)

    def on_stop(self) -> None:
        """Stop the process."""
        if self.worker:
            self.worker.stop()


class ProcessWorker(QRunnable):
    """Worker for running the process."""

    def __init__(self, signals: WorkerSignals, bus: MessageBus, cmd: Command) -> None:
        """Initialize the worker."""
        super().__init__()
        self.signals = signals
        self.bus = bus
        self.cmd = cmd

    def run(self) -> None:
        """Run the process."""
        self.bus.handle(self.cmd)
        self.signals.process_started.emit()
        self.signals.finished.emit()

    def stop(self) -> None:
        """Stop the process."""
        self.signals.stopped.emit()
