"""Observer for GUI."""

from dataclasses import dataclass

from PySide6.QtCore import QObject, Signal

from ..core import Observer


class WorkerSignals(QObject):
    """Qt worker signals."""

    progress_total = Signal(int)
    count_total = Signal()
    progress = Signal(int)
    finished = Signal()
    log = Signal(str)
    count = Signal(int)


@dataclass(slots=True)
class GuiObserver(Observer):
    """GUI observer."""

    signals: WorkerSignals

    def on_progress_total(self, maximum: int) -> None:
        """Emit total progress signal."""
        self.signals.progress_total.emit(maximum)

    def on_count_total(self) -> None:
        """Emit total count signal."""
        self.signals.count_total.emit()

    def on_progress(self, maximum: int) -> None:
        """Emit progress signal."""
        self.signals.progress.emit(maximum)

    def on_finished(self) -> None:
        """Emit finished signal."""
        self.signals.finished.emit()

    def on_log(self, msg: str) -> None:
        """Emit log message signal."""
        self.signals.log.emit(msg)

    def on_count(self, count: int) -> None:
        """Emit count update signal."""
        self.signals.count.emit(count)
