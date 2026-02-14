"""Workers for GUI."""

from typing import TYPE_CHECKING

from PySide6.QtCore import QRunnable, Slot

from ..core import build_engine
from .observer import GuiObserver, WorkerSignals

if TYPE_CHECKING:
    from ..core import ConfigModel, Engine


class MainWorker(QRunnable):
    """Worker for running process."""

    def __init__(self, config: ConfigModel) -> None:
        """Initialize the worker."""
        super().__init__()
        self.signals = WorkerSignals()
        self.engine: Engine = build_engine(config, observer=GuiObserver(self.signals))

    @Slot()
    def run(self) -> None:
        """Run the process."""
        self.engine.start()

    def stop(self) -> None:
        """Stop the process."""
        self.engine.request_stop()
