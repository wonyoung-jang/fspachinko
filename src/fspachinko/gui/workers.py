"""Workers for GUI."""

from typing import TYPE_CHECKING

from PySide6.QtCore import QRunnable, Slot

from ..core import build_engine
from .observer import GuiObserver, WorkerSignals

if TYPE_CHECKING:
    from ..config import ConfigModel
    from ..core import Engine


class MainWorker(QRunnable):
    """Worker for running process."""

    def __init__(self, signals: WorkerSignals, engine: Engine) -> None:
        """Initialize the worker."""
        super().__init__()
        self.signals = signals
        self.engine = engine

    @classmethod
    def from_config(cls, config: ConfigModel) -> MainWorker:
        """Post-initialization tasks."""
        signals = WorkerSignals()
        observer = GuiObserver(signals)
        engine = build_engine(config)
        engine.set_observer(observer)
        return cls(signals, engine)

    @Slot()
    def run(self) -> None:
        """Run the process."""
        self.engine.start()

    def stop(self) -> None:
        """Stop the process."""
        self.engine.request_stop()
