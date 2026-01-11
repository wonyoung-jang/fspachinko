"""Workers for mandala GUI."""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from random import Random
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QThread, Signal

from ..core.engine import MandalaEngine
from ..core.logger import MandalaLogger
from ..core.state import MandalaState
from ..core.validator import FileValidator

if TYPE_CHECKING:
    from mandala.core.config import MandalaConfig


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

    config: InitVar[MandalaConfig]
    engine: MandalaEngine = field(init=False)
    observer: MandalaQtSignalObserver = field(default_factory=MandalaQtSignalObserver)

    def __post_init__(self, config: MandalaConfig) -> None:
        """Initialize the worker thread."""
        super().__init__()
        state = MandalaState()
        validator = FileValidator(config)
        logger = MandalaLogger(config, state)
        self.engine = MandalaEngine(
            config=config,
            state=state,
            validator=validator,
            logger=logger,
            stop_requested=False,
            rng=Random(x=Random().randint(0, 2**32 - 1)),
        )
        self.engine.set_observer(self.observer)

    def run(self) -> None:
        """Run the Mandala process."""
        self.engine.start()

    def stop(self) -> None:
        """Stop the Mandala process."""
        self.engine.request_stop()
