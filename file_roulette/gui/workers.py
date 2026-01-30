"""Workers for file-roulette GUI."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from PySide6.QtCore import QThread, Slot

from ..core import build_engine
from .observer import GuiObserver, WorkerSignals

if TYPE_CHECKING:
    from ..config import ConfigModel
    from ..core import Engine


@dataclass(slots=True)
class MainWorker:
    """Worker for running File Roulette."""

    signals: WorkerSignals
    engine: Engine

    @classmethod
    def from_config(cls, config: ConfigModel, signals: WorkerSignals) -> MainWorker:
        """Post-initialization tasks."""
        observer = GuiObserver(signals)
        engine = build_engine(config)
        engine.set_observer(observer)
        return cls(signals, engine)

    def request_run(self) -> None:
        """Run the File Roulette process."""
        self.engine.start()

    def request_stop(self) -> None:
        """Stop the File Roulette process."""
        self.engine.request_stop()


@dataclass(slots=True)
class MainThread(QThread):
    """Worker thread for running File Roulette."""

    worker: MainWorker

    def __post_init__(self) -> None:
        """Initialize the worker thread."""
        super().__init__()

    @Slot()
    def run(self) -> None:
        """Run the File Roulette process."""
        self.worker.request_run()

    def stop(self) -> None:
        """Stop the File Roulette process."""
        self.worker.request_stop()
