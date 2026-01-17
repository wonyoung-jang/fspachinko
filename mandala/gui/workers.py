"""Workers for mandala GUI."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QThread, Signal

from ..core.builder import build_engine
from ..utils.interfaces import MandalaObserver

if TYPE_CHECKING:
    from ..config.config import MandalaConfig
    from ..core.engine import MandalaEngine


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

    signals: WorkerSignals = field(default_factory=WorkerSignals)

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
class RunMandalaWorker(QThread):
    """Worker thread for running Mandala."""

    config: MandalaConfig
    engine: MandalaEngine = field(init=False)
    observer: GuiObserver = field(default_factory=GuiObserver)

    def __post_init__(self) -> None:
        """Initialize the worker thread."""
        super().__init__()

    def init_engine(self) -> None:
        """Initialize the Mandala engine."""
        self.engine = build_engine(self.config)
        self.engine.set_observer(self.observer)

    def run(self) -> None:
        """Run the Mandala process."""
        self.init_engine()
        self.engine.start()

    def stop(self) -> None:
        """Stop the Mandala process."""
        self.engine.request_stop()
