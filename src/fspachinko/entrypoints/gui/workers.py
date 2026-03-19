"""Workers for GUI."""

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

from fspachinko.adapters.loggers import get_dest_log_filehandler
from fspachinko.adapters.pipeline import TransferPipeline
from fspachinko.bootstrap import bootstrap
from fspachinko.configuration.model import ConfigModel, RangeFilterModel
from fspachinko.constants import SIZE_MAP, TIME_MAP, FilterName, ReStrFmt
from fspachinko.domain.commands import (
    Command,
    CreateDirnameFn,
    CreateFilecountFn,
    CreateFilefilterFn,
    CreateFilenameFn,
    CreateRangeFilterFn,
    CreateTextFilterFn,
    CreateTransferFn,
    CreateWalkerFn,
    ProcessDirectory,
    StopProcess,
)
from fspachinko.domain.events import FileTransferred

if TYPE_CHECKING:
    from collections.abc import Iterator

    from fspachinko.service.messagebus import MessageBus


class WorkerSignals(QObject):
    """Qt worker signals."""

    process_started = Signal(int)
    directory_started = Signal(int)
    file_transferred = Signal()
    finished = Signal()


class ProcessController(QObject):
    """Qt worker signals."""

    def __init__(self) -> None:
        """Initialize the process controller."""
        super().__init__()
        self.signals = WorkerSignals()
        self.threadpool = QThreadPool()
        self.worker: MainWorker | None = None

    def start(self, config: dict) -> None:
        """Start the process."""
        self.worker = MainWorker(ConfigModel.from_dict(config), self.signals)
        self.worker.setAutoDelete(False)
        self.threadpool.start(self.worker)

    def stop(self) -> None:
        """Stop the process."""
        if self.worker is not None:
            self.worker.stop()


def _setup_commands(c: ConfigModel) -> Iterator[Command]:
    yield from (
        CreateTransferFn(c.options.transfer_mode),
        CreateFilenameFn(c.filename.template, c.filename.is_enabled),
        CreateFilecountFn(c.filecount.count, (c.filecount.rand_min, c.filecount.rand_max), c.filecount.is_rand_enabled),
        CreateDirnameFn(c.dest, c.directory.name, c.directory.is_enabled),
        CreateWalkerFn(c.root, c.options.should_follow_symlink),
    )
    text_specs = [
        (FilterName.DIRNAME, c.dirname, ReStrFmt.DIRECTORY),
        (FilterName.KEYWORD, c.keyword, ReStrFmt.KEYWORD),
        (FilterName.EXTENSION, c.extension, ReStrFmt.EXTENSION),
    ]
    for name, model, fmt in text_specs:
        yield CreateTextFilterFn(name, model.text, fmt, model.is_enabled, model.should_include)
    range_specs: list[tuple[str, RangeFilterModel, dict]] = [
        (FilterName.FILESIZE, c.filesize, SIZE_MAP),
        (FilterName.DURATION, c.duration, TIME_MAP),
    ]
    for name, model, unit_map in range_specs:
        mul = unit_map.get(model.unit, 1.0)
        yield CreateRangeFilterFn(name, model.minimum * mul, model.maximum * mul, model.is_enabled)
    yield CreateFilefilterFn()


def _setup_bus(bus: MessageBus, config: ConfigModel) -> None:
    """Bootstrap the application."""
    for cmd in _setup_commands(config):
        bus.handle(cmd)


class MainWorker(QRunnable):
    """Worker for running process."""

    def __init__(self, config: ConfigModel, signals: WorkerSignals) -> None:
        """Initialize the worker."""
        super().__init__()
        self.config = config
        self.signals = signals
        self.bus: MessageBus | None = None

    @Slot()
    def run(self) -> None:
        """Run the process."""
        pipeline = TransferPipeline(is_create_dir=self.config.directory.is_enabled)
        self.bus = bootstrap(m=self.config, pipeline=pipeline)
        self.bus.event_handlers[FileTransferred].append(lambda _: self.signals.file_transferred.emit())
        _setup_bus(self.bus, self.config)
        root_logger = logging.getLogger()
        self.signals.process_started.emit(self.config.directory.count)
        for _ in range(self.config.directory.count):
            dest_dir = pipeline.get_currdir_dest()
            target_qty = pipeline.filecount_fn()
            self.signals.directory_started.emit(target_qty)
            handler = get_dest_log_filehandler(dest_dir)
            root_logger.addHandler(handler)
            self.bus.handle(ProcessDirectory(dest_dir, target_qty))
            root_logger.removeHandler(handler)
            handler.close()
        self.signals.finished.emit()

    def stop(self) -> None:
        """Stop the process."""
        if self.bus is not None:
            self.bus.handle(StopProcess())
