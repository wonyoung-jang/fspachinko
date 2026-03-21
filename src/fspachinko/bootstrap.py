"""Builder module for core functionality."""

import logging
from dataclasses import dataclass, field
from random import seed
from typing import TYPE_CHECKING

from fspachinko.adapters.pipeline import AbstractPipeline, TransferPipeline

from .constants import SIZE_MAP, TIME_MAP, FilterName, ReStrFmt
from .domain.commands import (
    Command,
    CreateDirnameFn,
    CreateFilecountFn,
    CreateFilefilterFn,
    CreateFilenameFn,
    CreateRangeFilterFn,
    CreateTextFilterFn,
    CreateTransferFn,
    CreateTransferJob,
    CreateWalkerFn,
    ProcessDirectory,
    SetPipelineCreateDir,
    SetRngSeed,
    StopProcess,
)
from .domain.events import DirectoryTransferred, FileTransferred
from .service.eventcollector import CompositeEventCollector
from .service.handlers import (
    CreateDirnameFnHandler,
    CreateFilecountFnHandler,
    CreateFilefilterFnHandler,
    CreateFilenameFnHandler,
    CreateRangeFilterFnHandler,
    CreateTextFilterFnHandler,
    CreateTransferFnHandler,
    CreateTransferJobHandler,
    CreateWalkerFnHandler,
    DirectoryTransferredHandler,
    FileTransferredHandler,
    ProcessDirectoryHandler,
    SetPipelineCreateDirHandler,
    SetRngSeedHandler,
    StopProcessHandler,
)
from .service.messagebus import MessageBus
from .service.uow import AbstractUnitOfWork, FileSystemUnitOfWork

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from .configuration.model import ConfigModel, RangeFilterModel


logger = logging.getLogger(__name__)


def setup_bus(bus: MessageBus, c: ConfigModel) -> None:
    """Bootstrap the application."""

    def _setup_commands() -> Iterator[Command]:
        yield from (
            SetRngSeed(c.options.rng_seed),
            SetPipelineCreateDir(c.directory.is_enabled),
            CreateTransferFn(c.options.transfer_mode),
            CreateFilenameFn(c.filename.template, c.filename.is_enabled),
            CreateFilecountFn(
                c.filecount.count, (c.filecount.rand_min, c.filecount.rand_max), c.filecount.is_rand_enabled
            ),
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
        yield CreateTransferJob(
            root=c.root, max_per_dir=c.options.max_per_dir, unique_files_only=c.options.is_create_unique_dirs
        )

    for cmd in _setup_commands():
        bus.handle(cmd)


@dataclass(slots=True)
class FSPachinkoBootstrapper:
    """Bootstrapper for the FSPachinko application."""

    collector: CompositeEventCollector = field(default_factory=CompositeEventCollector)
    pipeline: AbstractPipeline = field(default_factory=TransferPipeline)
    fs_uow: AbstractUnitOfWork = field(default_factory=FileSystemUnitOfWork)
    log_fn: Callable = logger.info
    rng_seed_fn: Callable = seed
    bus: MessageBus = field(init=False)

    def __post_init__(self) -> None:
        """Post-initialization to set up the message bus."""
        if not isinstance(self.fs_uow, FileSystemUnitOfWork):
            msg = "Unit of Work must be provided if pipeline is not a TransferPipeline."
            raise TypeError(msg)
        self.collector.register_emitter(self.fs_uow)
        event_handlers = {
            FileTransferred: [FileTransferredHandler(log_fn=self.log_fn)],
            DirectoryTransferred: [DirectoryTransferredHandler(log_fn=self.log_fn)],
        }
        command_handlers = {
            CreateTransferJob: CreateTransferJobHandler(uow=self.fs_uow),
            ProcessDirectory: ProcessDirectoryHandler(uow=self.fs_uow, pipeline=self.pipeline),
            StopProcess: StopProcessHandler(uow=self.fs_uow),
            SetRngSeed: SetRngSeedHandler(rng_seed_fn=self.rng_seed_fn),
            SetPipelineCreateDir: SetPipelineCreateDirHandler(pipeline=self.pipeline),
            CreateTransferFn: CreateTransferFnHandler(pipeline=self.pipeline),
            CreateFilenameFn: CreateFilenameFnHandler(pipeline=self.pipeline),
            CreateFilecountFn: CreateFilecountFnHandler(pipeline=self.pipeline),
            CreateDirnameFn: CreateDirnameFnHandler(pipeline=self.pipeline),
            CreateWalkerFn: CreateWalkerFnHandler(pipeline=self.pipeline),
            CreateTextFilterFn: CreateTextFilterFnHandler(pipeline=self.pipeline),
            CreateRangeFilterFn: CreateRangeFilterFnHandler(pipeline=self.pipeline),
            CreateFilefilterFn: CreateFilefilterFnHandler(pipeline=self.pipeline),
        }
        self.bus = MessageBus(
            collector=self.collector,
            event_handlers=event_handlers,
            command_handlers=command_handlers,
        )
