"""Workers for GUI."""

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from ..bootstrap import bootstrap, build_pipeline
from ..domain.commands import StartProcessingDirectory, StopProcess
from ..domain.events import DirectoryTransferred, Event, FileTransferred

if TYPE_CHECKING:
    from ..config import ConfigModel
    from ..service.messagebus import MessageBus

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
        self.bus: MessageBus | None = None

    @Slot()
    def run(self) -> None:
        """Run the process."""
        m = self.config
        pipeline = build_pipeline(m)
        self.bus = bootstrap(m=m, pipeline=pipeline)

        def publish(event: Event) -> None:
            if isinstance(event, FileTransferred):
                self.signals.file_transferred.emit(event.count)
                logger.info("%s: %s -> %s", event.count, event.src, event.dst)
            elif isinstance(event, DirectoryTransferred):
                logger.info("%s\n%s", event.status, event.report)

        bus = self.bus
        dir_count = m.directory.count

        self.signals.start_process.emit(dir_count)

        for dir_idx in range(1, dir_count + 1):
            target_qty = pipeline.get_file_count()

            self.signals.directory_start.emit(dir_idx, target_qty)

            start_process_cmd = StartProcessingDirectory(dir_idx=dir_idx, target_qty=target_qty)
            bus.handle(start_process_cmd, uow=bus.uow, publish=publish)

        self.signals.finished.emit()

    def stop(self) -> None:
        """Stop the process."""
        if self.bus is not None:
            stop_cmd = StopProcess()
            self.bus.handle(stop_cmd, uow=self.bus.uow)
