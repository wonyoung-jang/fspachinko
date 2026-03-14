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
    directory_start = Signal(int, int)
    file_transferred = Signal(int)
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

        def handle_file_transferred(e: FileTransferred, **_: object) -> None:
            self.signals.file_transferred.emit(e.count)

        self.bus.event_handlers[FileTransferred].append(handle_file_transferred)

        self.signals.start_process.emit(self.config.directory.count)

        for dir_idx in range(1, self.config.directory.count + 1):
            dest_dir = self.bus.uow.pipeline.get_currdir_dest()
            target_qty = self.bus.uow.pipeline.filecount_fn()

            self.signals.directory_start.emit(dir_idx, target_qty)

            handler = get_dest_log_filehandler(dest_dir)
            logging.getLogger().addHandler(handler)

            start_process_cmd = StartProcessingDirectory(dest_dir, target_qty)
            self.bus.handle(start_process_cmd, uow=self.bus.uow)

            logging.getLogger().removeHandler(handler)
            handler.close()

        self.signals.finished.emit()

    def stop(self) -> None:
        """Stop the process."""
        if self.bus is not None:
            stop_cmd = StopProcess()
            self.bus.handle(stop_cmd, uow=self.bus.uow)
