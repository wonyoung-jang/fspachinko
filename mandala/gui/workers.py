"""Workers for mandala GUI."""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from random import Random
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QThread, Signal

from ..core.engine import MandalaEngine
from ..core.logger import MandalaLogger
from ..core.quota import DiversityQuota
from ..core.state import MandalaState
from ..core.validator import FileValidator
from ..core.walker import RandomFSWalker

if TYPE_CHECKING:
    from ..core.config import MandalaConfig


class WorkerSignals(QObject):
    """Qt signal observer implementation for Mandala."""

    progress = Signal(int)
    finished = Signal()
    log = Signal(str)
    time = Signal()
    count = Signal(int)

    def on_progress(self, maximum: int) -> None:
        """Emit progress signal."""
        self.progress.emit(maximum)

    def on_finished(self) -> None:
        """Emit finished signal."""
        self.finished.emit()

    def on_log(self, msg: str) -> None:
        """Emit log message signal."""
        self.log.emit(msg)

    def on_time(self) -> None:
        """Emit time update signal."""
        self.time.emit()

    def on_count(self, count: int) -> None:
        """Emit count update signal."""
        self.count.emit(count)


@dataclass(slots=True)
class RunMandalaWorker(QThread):
    """Worker thread for running Mandala."""

    config: InitVar[MandalaConfig]
    engine: MandalaEngine = field(init=False)
    signals: WorkerSignals = field(default_factory=WorkerSignals)

    def __post_init__(self, config: MandalaConfig) -> None:
        """Initialize the worker thread."""
        super().__init__()
        self.init_engine(config)

    def init_engine(self, config: MandalaConfig) -> None:
        """Initialize the Mandala engine."""
        state = MandalaState()
        validator = FileValidator(config)
        logger = MandalaLogger(config, state)
        quota = DiversityQuota(
            root=config.root,
            limit_root_folder=config.diversity_model.root_limit,
            limit_leaf_folder=config.diversity_model.leaf_limit,
        )

        sys_rand = Random()
        rng_seed = sys_rand.randint(0, 2**32 - 1)
        rng = Random(rng_seed)

        walker = RandomFSWalker(
            root=config.root,
            rng=rng,
            quota=quota,
            trash_empty_folders=config.trash_model.empty_folder,
        )

        self.engine = MandalaEngine(
            config=config,
            state=state,
            validator=validator,
            logger=logger,
            stop_requested=False,
            rng=rng,
            quota=quota,
            walker=walker,
        )
        self.engine.set_observer(self.signals)

    def run(self) -> None:
        """Run the Mandala process."""
        if self.engine:
            self.engine.start()

    def stop(self) -> None:
        """Stop the Mandala process."""
        if self.engine:
            self.engine.request_stop()
