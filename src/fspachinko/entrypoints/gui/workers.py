"""Workers for GUI."""

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

from fspachinko.adapters.loggers import get_dest_log_filehandler
from fspachinko.bootstrap import setup_bus
from fspachinko.domain.commands import ProcessDirectory, StopProcess
from fspachinko.domain.events import FileTransferred

if TYPE_CHECKING:
    from fspachinko.adapters.pipeline import AbstractPipeline
    from fspachinko.configuration.model import ConfigModel
    from fspachinko.service.messagebus import MessageBus


class WorkerSignals(QObject):
    """Qt worker signals."""

    process_started = Signal(int)
    directory_started = Signal(int)
    file_transferred = Signal()
    finished = Signal()


class ProcessController(QObject):
    """Qt worker signals."""

    def __init__(self) -> None:
        """Initialize the process controller."""
        super().__init__()
        self.signals = WorkerSignals()
        self.threadpool = QThreadPool()
        self.worker: MainWorker | None = None

    def start(self, bus: MessageBus, pipeline: AbstractPipeline, config: ConfigModel) -> None:
        """Start the process."""
        self.worker = MainWorker(bus, pipeline, config, self.signals)
        self.worker.setAutoDelete(False)
        self.threadpool.start(self.worker)

    def stop(self) -> None:
        """Stop the process."""
        if self.worker is not None:
            self.worker.stop()
            self.worker = None


class MainWorker(QRunnable):
    """Worker for running process."""

    def __init__(
        self, bus: MessageBus, pipeline: AbstractPipeline, config: ConfigModel, signals: WorkerSignals
    ) -> None:
        """Initialize the worker."""
        super().__init__()
        self.bus = bus
        self.pipeline = pipeline
        self.config = config
        self.signals = signals

    @Slot()
    def run(self) -> None:
        """Run the process."""
        self.bus.event_handlers[FileTransferred].append(lambda _: self.signals.file_transferred.emit())
        setup_bus(self.bus, self.config)
        root_logger = logging.getLogger()
        self.signals.process_started.emit(self.config.directory.count)
        for dest_dir in self.pipeline.dirnames:
            target_qty = self.pipeline.filecount_fn()
            self.signals.directory_started.emit(target_qty)
            handler = get_dest_log_filehandler(dest_dir)
            root_logger.addHandler(handler)
            self.bus.handle(ProcessDirectory(dest_dir, target_qty))
            root_logger.removeHandler(handler)
            handler.close()
        self.signals.finished.emit()

    def stop(self) -> None:
        """Stop the process."""
        self.bus.handle(StopProcess())
