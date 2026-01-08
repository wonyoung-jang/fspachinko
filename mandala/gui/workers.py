"""Workers for mandala GUI."""

from __future__ import annotations  # noqa: I001

from dataclasses import dataclass
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QRunnable, Signal

# noinspection PyUnresolvedReferences
from __feature__ import snake_case, true_property  # type: ignore[reportMissingImports] # noqa: F401


if TYPE_CHECKING:
    from mandala.gui.main_window import MandalaMainGui


class WorkerSignals(QObject):
    """Defines the signals available from a running worker thread."""

    count_signal = Signal()
    log_signal = Signal(object)
    time_signal = Signal()
    finished_signal = Signal()


@dataclass(slots=True)
class RunMandalaWorker(QRunnable):
    """Worker thread for running Mandala."""

    window: MandalaMainGui

    def __post_init__(self) -> None:
        """Initialize the worker thread."""
        super().__init__()

    def run(self) -> None:
        """Run the Mandala process."""
        # self.window.engine.start()
        self.window.start()
