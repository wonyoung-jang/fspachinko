"""Workers for mandala GUI."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QThread, Signal, Slot

from ..core import build_engine
from ..utils.interfaces import MandalaObserver

if TYPE_CHECKING:
    from ..config.schemas import MandalaConfigModel
    from ..core import MandalaEngine


class WorkerSignals(QObject):
    """Qt signal observer implementation for Mandala."""

    progress_total = Signal(int)
    count_total = Signal()
    progress = Signal(int)
    finished = Signal()
    log = Signal(str)
    time = Signal()
    count = Signal(int)


@dataclass(slots=True)
class GuiObserver(MandalaObserver):
    """Qt signal observer implementation for Mandala."""

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

    def on_time(self) -> None:
        """Emit time update signal."""
        self.signals.time.emit()

    def on_count(self, count: int) -> None:
        """Emit count update signal."""
        self.signals.count.emit(count)


@dataclass(slots=True)
class MandalaWorker:
    """Worker for running Mandala."""

    signals: WorkerSignals
    engine: MandalaEngine

    @classmethod
    def from_config(cls, config: MandalaConfigModel, signals: WorkerSignals) -> MandalaWorker:
        """Post-initialization tasks."""
        observer = GuiObserver(signals)
        engine = build_engine(config)
        engine.set_observer(observer)
        return cls(signals, engine)

    def request_run(self) -> None:
        """Run the Mandala process."""
        self.engine.start()

    def request_stop(self) -> None:
        """Stop the Mandala process."""
        self.engine.request_stop()


@dataclass(slots=True)
class MandalaThread(QThread):
    """Worker thread for running Mandala."""

    worker: MandalaWorker

    def __post_init__(self) -> None:
        """Initialize the worker thread."""
        super().__init__()

    @Slot()
    def run(self) -> None:
        """Run the Mandala process."""
        self.worker.request_run()

    def stop(self) -> None:
        """Stop the Mandala process."""
        self.worker.request_stop()
