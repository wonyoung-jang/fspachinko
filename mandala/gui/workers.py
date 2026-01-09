"""Workers for mandala GUI."""

from __future__ import annotations  # noqa: I001

from dataclasses import dataclass

from PySide6.QtCore import QThread
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.mandala_engine import MandalaEngine


@dataclass(slots=True)
class RunMandalaWorker(QThread):
    """Worker thread for running Mandala."""

    engine: MandalaEngine

    def __post_init__(self) -> None:
        """Initialize the worker thread."""
        super().__init__()

    def run(self) -> None:
        """Run the Mandala process."""
        self.engine.start()

    def stop(self) -> None:
        """Stop the Mandala process."""
        self.engine.request_stop()
