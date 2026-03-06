"""Workers for GUI."""

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from ..bootstrap import bootstrap
from ..domain.commands import StartProcess, StopProcess
from ..domain.events import DirectoryStarted, FileTransferred, ProcessStarted, ProcessStopped

if TYPE_CHECKING:
    from ..config import ConfigModel
    from ..service.messagebus import MessageBus
    from ..service.uow import AbstractUnitOfWork


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
        self.signals = WorkerSignals()
        self.bus: MessageBus = bootstrap(m=config)

    @Slot()
    def run(self) -> None:
        """Run the process."""

        def update_start_process(event: ProcessStarted, _: AbstractUnitOfWork) -> None:
            self.signals.start_process.emit(event.dir_count)

        def update_file_transferred(event: FileTransferred, _: AbstractUnitOfWork) -> None:
            self.signals.file_transferred.emit(event.count)

        def update_directory_started(event: DirectoryStarted, _: AbstractUnitOfWork) -> None:
            self.signals.directory_start.emit(event.idx, event.target)

        def update_finished(_: ProcessStopped, __: AbstractUnitOfWork) -> None:
            self.signals.finished.emit()

        self.bus.event_handlers[ProcessStarted].append(update_start_process)
        self.bus.event_handlers[FileTransferred].append(update_file_transferred)
        self.bus.event_handlers[DirectoryStarted].append(update_directory_started)
        self.bus.event_handlers[ProcessStopped].append(update_finished)

        self.bus.handle(StartProcess())

    def stop(self) -> None:
        """Stop the process."""
        self.bus.handle(StopProcess())
