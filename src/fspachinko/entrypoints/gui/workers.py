"""Workers for GUI."""

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

from fspachinko.adapters.loggers import get_dest_log_filehandler
from fspachinko.bootstrap import setup_bus

if TYPE_CHECKING:
    from fspachinko.adapters.pipeline import AbstractPipeline
    from fspachinko.configuration.model import ConfigModel
    from fspachinko.service.messagebus import MessageBus

root_logger = logging.getLogger()


class WorkerSignals(QObject):
    """Qt worker signals."""

    process_started = Signal(int)
    file_transferred = Signal()
    finished = Signal()
    stopped = Signal()
    process_directory = Signal(str, int)


class ProcessController(QObject):
    """Qt worker signals."""

    def __init__(self, bus: MessageBus, pipeline: AbstractPipeline) -> None:
        """Initialize the process controller."""
        super().__init__()
        self.bus = bus
        self.pipeline = pipeline
        self.signals = WorkerSignals()
        self.threadpool = QThreadPool()
        self.worker: MainWorker | None = None

    def start(self, config: ConfigModel) -> None:
        """Start the process."""
        setup_bus(self.bus, config)
        self.worker = MainWorker(dest_dir_inputs=self.pipeline.dest_dir_inputs, signals=self.signals)
        self.worker.setAutoDelete(False)
        self.threadpool.start(self.worker)

    def stop(self) -> None:
        """Stop the process."""
        if self.worker is not None:
            self.worker.stop()
            self.worker = None


class MainWorker(QRunnable):
    """Worker for running process."""

    def __init__(self, dest_dir_inputs: list[tuple[str, int]], signals: WorkerSignals) -> None:
        """Initialize the worker."""
        super().__init__()
        self.dest_dir_inputs = dest_dir_inputs
        self.signals = signals

    def run(self) -> None:
        """Run the process."""
        self.signals.process_started.emit(len(self.dest_dir_inputs))
        for dest_dir, target_qty in self.dest_dir_inputs:
            handler = get_dest_log_filehandler(dest_dir)
            root_logger.addHandler(handler)
            self.signals.process_directory.emit(dest_dir, target_qty)
            root_logger.removeHandler(handler)
            handler.close()
        self.signals.finished.emit()

    def stop(self) -> None:
        """Stop the process."""
        self.signals.stopped.emit()
