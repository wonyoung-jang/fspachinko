"""Observer for GUI."""

from dataclasses import dataclass

from PySide6.QtCore import QObject, Signal

from ..core import Observer


class WorkerSignals(QObject):
    """Qt worker signals."""

    start_process = Signal(int)
    directory_start = Signal(int, int)
    file_transferred = Signal(int)
    finished = Signal()


@dataclass(slots=True)
class GuiObserver(Observer):
    """GUI observer."""

    signals: WorkerSignals

    def on_start_process(self, ndir_to_create: int) -> None:
        """Call when starting a run of the engine."""
        self.signals.start_process.emit(ndir_to_create)

    def on_directory_start(self, idx: int, nfiles_to_process: int) -> None:
        """Call when starting to process a directory."""
        self.signals.directory_start.emit(idx, nfiles_to_process)

    def on_file_transferred(self, count: int) -> None:
        """Call when a file is transferred."""
        self.signals.file_transferred.emit(count)

    def on_finished(self) -> None:
        """Call when processing is finished."""
        self.signals.finished.emit()
