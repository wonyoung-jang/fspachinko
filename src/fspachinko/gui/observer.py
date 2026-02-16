"""Observer for GUI."""

from dataclasses import dataclass

from PySide6.QtCore import QObject, Signal

from ..core import Observer


class WorkerSignals(QObject):
    """Qt worker signals."""

    progress_total = Signal(int)
    count_total = Signal(int)
    progress = Signal(int)
    count = Signal(int)
    finished = Signal()


@dataclass(slots=True)
class GuiObserver(Observer):
    """GUI observer."""

    signals: WorkerSignals

    def on_total_start(self, maximum: int) -> None:
        """Emit total progress signal."""
        self.signals.progress_total.emit(maximum)

    def on_directory_increment(self, count: int) -> None:
        """Emit total count signal."""
        self.signals.count_total.emit(count)

    def on_directory_start(self, maximum: int) -> None:
        """Emit progress signal."""
        self.signals.progress.emit(maximum)

    def on_file_increment(self, count: int) -> None:
        """Emit count update signal."""
        self.signals.count.emit(count)

    def on_finished(self) -> None:
        """Emit finished signal."""
        self.signals.finished.emit()
