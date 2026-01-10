"""Workers for mandala GUI."""

from __future__ import annotations  # noqa: I001

from dataclasses import dataclass, field

from PySide6.QtCore import QThread, Signal, QObject
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from ..core.mandala_engine import MandalaEngine


class MandalaQtSignalObserver(QObject):
    """Qt signal observer implementation for Mandala."""

    finished = Signal()
    log = Signal(str)
    time = Signal()
    count = Signal(int)

    def on_finished(self) -> None:
        """Emit finished signal."""
        self.finished.emit()

    def on_log(self, msg: str) -> None:
        """Emit log message signal."""
        self.log.emit(msg)

    def on_time(self) -> None:
        """Emit time update signal."""
        self.time.emit()

    def on_count(self, num: int) -> None:
        """Emit count update signal."""
        self.count.emit(num)


@dataclass(slots=True)
class RunMandalaWorker(QThread):
    """Worker thread for running Mandala."""

    engine: MandalaEngine
    observer: MandalaQtSignalObserver = field(init=False)

    def __post_init__(self) -> None:
        """Initialize the worker thread."""
        super().__init__()
        self.observer = MandalaQtSignalObserver()
        self.engine.set_observer(self.observer)

    def run(self) -> None:
        """Run the Mandala process."""
        self.engine.start()

    def stop(self) -> None:
        """Stop the Mandala process."""
        self.engine.request_stop()
