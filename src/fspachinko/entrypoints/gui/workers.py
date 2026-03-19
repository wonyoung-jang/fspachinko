"""Workers for GUI."""

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

from fspachinko.adapters.loggers import get_dest_log_filehandler
from fspachinko.adapters.pipeline import TransferPipeline
from fspachinko.bootstrap import bootstrap
from fspachinko.configuration.model import ConfigModel
from fspachinko.constants import SIZE_MAP, TIME_MAP, ReStrFmt
from fspachinko.domain.commands import (
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


class MainWorker(QRunnable):
    """Worker for running process."""

    def __init__(self, config: ConfigModel, signals: WorkerSignals) -> None:
        """Initialize the worker."""
        super().__init__()
        self.config = config
        self.signals = signals
        self.bus: MessageBus | None = None

    def _bootstrap(self) -> None:
        """Bootstrap the application."""
        if self.bus is None:
            msg = "Message bus is not initialized."
            raise ValueError(msg)
        self.bus.handle(
            CreateTransferFn(
                self.config.options.transfer_mode,
            )
        )
        self.bus.handle(
            CreateFilenameFn(
                self.config.filename.template,
                self.config.filename.is_enabled,
            )
        )
        self.bus.handle(
            CreateFilecountFn(
                self.config.filecount.count,
                (self.config.filecount.rand_min, self.config.filecount.rand_max),
                self.config.filecount.is_rand_enabled,
            )
        )
        self.bus.handle(
            CreateDirnameFn(
                self.config.dest,
                self.config.directory.name,
                self.config.directory.is_enabled,
            )
        )
        self.bus.handle(
            CreateWalkerFn(
                self.config.root,
                self.config.options.should_follow_symlink,
            )
        )
        self.bus.handle(
            CreateTextFilterFn(
                name="dirname_filter",
                text=self.config.dirname.text,
                re_fmt=ReStrFmt.DIRECTORY,
                is_enabled=self.config.dirname.is_enabled,
                should_include=self.config.dirname.should_include,
            )
        )
        self.bus.handle(
            CreateTextFilterFn(
                name="keyword_filter",
                text=self.config.keyword.text,
                re_fmt=ReStrFmt.KEYWORD,
                is_enabled=self.config.keyword.is_enabled,
                should_include=self.config.keyword.should_include,
            )
        )
        self.bus.handle(
            CreateTextFilterFn(
                name="extension_filter",
                text=self.config.extension.text,
                re_fmt=ReStrFmt.EXTENSION,
                is_enabled=self.config.extension.is_enabled,
                should_include=self.config.extension.should_include,
            )
        )
        self.bus.handle(
            CreateRangeFilterFn(
                name="filesize_filter",
                minimum=self.config.filesize.minimum * SIZE_MAP.get(self.config.filesize.unit, 1.0),
                maximum=self.config.filesize.maximum * SIZE_MAP.get(self.config.filesize.unit, 1.0),
                is_enabled=self.config.filesize.is_enabled,
            )
        )
        self.bus.handle(
            CreateRangeFilterFn(
                name="duration_filter",
                minimum=self.config.duration.minimum * TIME_MAP.get(self.config.duration.unit, 1.0),
                maximum=self.config.duration.maximum * TIME_MAP.get(self.config.duration.unit, 1.0),
                is_enabled=self.config.duration.is_enabled,
            )
        )
        self.bus.handle(CreateFilefilterFn())
        self.bus.event_handlers[FileTransferred].append(lambda _: self.signals.file_transferred.emit())

    @Slot()
    def run(self) -> None:
        """Run the process."""
        pipeline = TransferPipeline(is_create_dir=self.config.directory.is_enabled)
        self.bus = bootstrap(m=self.config, pipeline=pipeline)
        self._bootstrap()
        self.signals.process_started.emit(self.config.directory.count)
        for _ in range(self.config.directory.count):
            dest_dir = pipeline.get_currdir_dest()
            target_qty = pipeline.filecount_fn()
            self.signals.directory_started.emit(target_qty)
            handler = get_dest_log_filehandler(dest_dir)
            logging.getLogger().addHandler(handler)
            start_process_cmd = ProcessDirectory(dest_dir, target_qty)
            self.bus.handle(start_process_cmd)
            logging.getLogger().removeHandler(handler)
            handler.close()
        self.signals.finished.emit()

    def stop(self) -> None:
        """Stop the process."""
        if self.bus is not None:
            stop_cmd = StopProcess()
            self.bus.handle(stop_cmd)
