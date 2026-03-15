"""Workers for GUI."""

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from ..adapters.loggers import get_dest_log_filehandler
from ..bootstrap import bootstrap, build_pipeline
from ..domain.commands import StartProcessingDirectory, StopProcess
from ..domain.events import FileTransferred

if TYPE_CHECKING:
    from ..config import ConfigModel


class WorkerSignals(QObject):
    """Qt worker signals."""

    start_process = Signal(int)
    directory_start = Signal(int)
    file_transferred = Signal()
    finished = Signal()


class MainWorker(QRunnable):
    """Worker for running process."""

    def __init__(self, config: ConfigModel) -> None:
        """Initialize the worker."""
        super().__init__()
        self.config = config
        self.signals = WorkerSignals()
        pipeline = build_pipeline(self.config)
        self.bus = bootstrap(m=self.config, pipeline=pipeline)

    @Slot()
    def run(self) -> None:
        """Run the process."""
        self.bus.event_handlers[FileTransferred].append(lambda _: self.signals.file_transferred.emit())

        self.signals.start_process.emit(self.config.directory.count)

        for _ in range(self.config.directory.count):
            dest_dir = self.bus.uow.pipeline.get_currdir_dest()
            target_qty = self.bus.uow.pipeline.get_target_filecount()

            self.signals.directory_start.emit(target_qty)

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
