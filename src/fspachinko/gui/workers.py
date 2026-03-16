"""Workers for GUI."""

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from ..adapters.loggers import get_dest_log_filehandler
from ..bootstrap import bootstrap, build_pipeline
from ..domain.commands import StartProcessingDirectory, StopProcess
from ..domain.events import FileTransferred

if TYPE_CHECKING:
    from ..configuration.model import ConfigModel
    from ..service.messagebus import MessageBus


class WorkerSignals(QObject):
    """Qt worker signals."""

    process_started = Signal(int)
    directory_started = Signal(int)
    file_transferred = Signal()
    finished = Signal()


class MainWorker(QRunnable):
    """Worker for running process."""

    def __init__(self) -> None:
        """Initialize the worker."""
        super().__init__()
        self.signals = WorkerSignals()
        self.bus: MessageBus | None = None

    @Slot()
    def run(self, config: ConfigModel) -> None:
        """Run the process."""
        pipeline = build_pipeline(config)
        self.bus = bootstrap(m=config, pipeline=pipeline)
        self.bus.event_handlers[FileTransferred].append(lambda _: self.signals.file_transferred.emit())

        self.signals.process_started.emit(config.directory.count)

        for _ in range(config.directory.count):
            dest_dir = self.bus.uow.pipeline.get_currdir_dest()
            target_qty = self.bus.uow.pipeline.get_target_filecount()

            self.signals.directory_started.emit(target_qty)

            handler = get_dest_log_filehandler(dest_dir)
            logging.getLogger().addHandler(handler)

            start_process_cmd = StartProcessingDirectory(dest_dir, target_qty)
            self.bus.handle(start_process_cmd)

            logging.getLogger().removeHandler(handler)
            handler.close()

        self.signals.finished.emit()

    def stop(self) -> None:
        """Stop the process."""
        if self.bus is not None:
            stop_cmd = StopProcess()
            self.bus.handle(stop_cmd)
