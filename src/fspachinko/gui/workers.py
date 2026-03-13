"""Workers for GUI."""

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from ..bootstrap import bootstrap, build_pipeline
from ..domain.commands import StartProcessingDirectory, StopProcess
from ..domain.events import FileTransferred

if TYPE_CHECKING:
    from ..config import ConfigModel

logger = logging.getLogger(__name__)


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
        m = self.config
        dir_count = m.directory.count
        bus = self.bus
        pipeline = bus.uow.pipeline

        def handle_file_transferred(e: FileTransferred, **_: object) -> None:
            self.signals.file_transferred.emit(e.count)

        bus.event_handlers[FileTransferred].append(handle_file_transferred)

        self.signals.start_process.emit(dir_count)

        for dir_idx in range(1, dir_count + 1):
            dest_dir = pipeline.get_currdir_dest()
            target_qty = pipeline.filecount_fn()

            self.signals.directory_start.emit(dir_idx, target_qty)

            pipeline.add_handler(dest_dir)

            start_process_cmd = StartProcessingDirectory(dest_dir, target_qty)
            bus.handle(start_process_cmd, uow=bus.uow)

            pipeline.remove_handler()

        self.signals.finished.emit()

    def stop(self) -> None:
        """Stop the process."""
        if self.bus is not None:
            stop_cmd = StopProcess()
            self.bus.handle(stop_cmd, uow=self.bus.uow)
