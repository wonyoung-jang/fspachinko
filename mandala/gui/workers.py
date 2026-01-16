"""Workers for mandala GUI."""

from __future__ import annotations

from dataclasses import dataclass, field
from random import Random
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QThread, Signal

from ..core.engine import MandalaEngine
from ..core.quota import DiversityQuota
from ..core.reporter import ReportWriter
from ..core.state import MandalaState
from ..core.validator import FileValidator
from ..core.walker import RandomFSWalker
from ..utils.interfaces import MandalaObserver

if TYPE_CHECKING:
    from ..config.config import MandalaConfig


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
class RunMandalaWorker(QThread):
    """Worker thread for running Mandala."""

    config: MandalaConfig
    engine: MandalaEngine = field(init=False)
    signals: WorkerSignals = field(init=False)
    observer: GuiObserver = field(init=False)

    def __post_init__(self) -> None:
        """Initialize the worker thread."""
        super().__init__()
        self.signals = WorkerSignals()
        self.observer = GuiObserver(signals=self.signals)

    def init_engine(self) -> None:
        """Initialize the Mandala engine."""
        cfg = self.config
        state = MandalaState()
        validator = FileValidator(cfg)
        reporter = ReportWriter(cfg)
        quota = DiversityQuota(
            root=cfg.root,
            limit_root_folder=cfg.diversity.root_limit,
            limit_leaf_folder=cfg.diversity.leaf_limit,
        )

        sys_rand = Random()
        rng_seed = sys_rand.randint(0, 2**32 - 1)
        rng = Random(rng_seed)

        walker = RandomFSWalker(
            root=cfg.root,
            rng=rng,
            quota=quota,
            trash_empty_folders=cfg.trash.empty_folder,
        )

        self.engine = MandalaEngine(
            config=cfg,
            state=state,
            validator=validator,
            reporter=reporter,
            rng=rng,
            quota=quota,
            walker=walker,
        )
        self.engine.set_observer(self.observer)

    def run(self) -> None:
        """Run the Mandala process."""
        self.init_engine()
        self.engine.start()

    def stop(self) -> None:
        """Stop the Mandala process."""
        self.engine.request_stop()
