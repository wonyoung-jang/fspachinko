"""Builder module for core functionality."""

import logging
from dataclasses import dataclass, field
from random import seed
from typing import TYPE_CHECKING, Any

from .adapters.pipeline import AbstractPipeline, TransferPipeline
from .constants import SIZE_MAP, TIME_MAP, FilterName, ReStrFmt
from .domain.commands import (
    Command,
    CreateDirnamesFn,
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
from .domain.events import DirectoryTransferred, Event, FileTransferred
from .service.eventcollector import CompositeEventCollector
from .service.handlers import (
    CreateDirnamesFnHandler,
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


def bootstrap(*args: Any, **kwargs: Any) -> tuple[MessageBus, AbstractPipeline]:
    """Bootstrap the application and return the message bus."""
    return FSPachinkoBootstrapper.bootstrap(*args, **kwargs)


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
            CreateDirnamesFn(c.directory.count, c.dest, c.directory.name, c.directory.is_enabled),
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

    @classmethod
    def bootstrap(cls, *args: Any, **kwargs: Any) -> tuple[MessageBus, AbstractPipeline]:
        """Bootstrap the application and return the message bus."""
        b = cls(*args, **kwargs)
        b.collector.register_emitter(b.fs_uow)
        return MessageBus(
            collector=b.collector,
            event_handlers=b.event_handlers,
            command_handlers=b.command_handlers,
        ), b.pipeline

    @property
    def event_handlers(self) -> dict[type[Event], list[Callable]]:
        """Get the event handlers."""
        log_fn = self.log_fn
        return {
            FileTransferred: [FileTransferredHandler(log_fn=log_fn)],
            DirectoryTransferred: [DirectoryTransferredHandler(log_fn=log_fn)],
        }

    @property
    def command_handlers(self) -> dict[type[Command], Callable]:
        """Get the command handlers."""
        uow, pipeline, rng_seed_fn = self.fs_uow, self.pipeline, self.rng_seed_fn
        return {
            CreateTransferJob: CreateTransferJobHandler(uow=uow),
            ProcessDirectory: ProcessDirectoryHandler(uow=uow, pipeline=pipeline),
            StopProcess: StopProcessHandler(uow=uow),
            SetRngSeed: SetRngSeedHandler(rng_seed_fn=rng_seed_fn),
            SetPipelineCreateDir: SetPipelineCreateDirHandler(pipeline=pipeline),
            CreateTransferFn: CreateTransferFnHandler(pipeline=pipeline),
            CreateFilenameFn: CreateFilenameFnHandler(pipeline=pipeline),
            CreateFilecountFn: CreateFilecountFnHandler(pipeline=pipeline),
            CreateDirnamesFn: CreateDirnamesFnHandler(pipeline=pipeline),
            CreateWalkerFn: CreateWalkerFnHandler(pipeline=pipeline),
            CreateTextFilterFn: CreateTextFilterFnHandler(pipeline=pipeline),
            CreateRangeFilterFn: CreateRangeFilterFnHandler(pipeline=pipeline),
            CreateFilefilterFn: CreateFilefilterFnHandler(pipeline=pipeline),
        }
