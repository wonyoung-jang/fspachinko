"""Builder module for core functionality."""

import logging
from dataclasses import dataclass, field
from random import seed
from typing import TYPE_CHECKING, Any

from fspachinko.configuration.uow import AbstractConfigUnitOfWork, JSONConfigUnitOfWork
from fspachinko.domain.commands import RunTransferJob, SaveProfile
from fspachinko.domain.events import DirectoryStarted
from fspachinko.service.handlers import DirectoryStartedHandler, RunTransferJobHandler, SaveProfileHandler

from .adapters.pipeline import AbstractPipeline, TransferPipeline
from .constants import SIZE_MAP, TIME_MAP, FilterName, ReStrFmt
from .domain.commands import (
    Command,
    CreateDestDirs,
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
    CreateDestDirsHandler,
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
from .service.uow import AbstractTransferUnitOfWork, TransferUnitOfWork

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from .configuration.model import ConfigModel


logger = logging.getLogger(__name__)


def bootstrap(*args: Any, **kwargs: Any) -> tuple[MessageBus, AbstractPipeline]:
    """Bootstrap the application and return the message bus."""
    return FSPachinkoBootstrapper.bootstrap(*args, **kwargs)


def setup_bus(bus: MessageBus, c: ConfigModel) -> None:
    """Bootstrap the application."""

    def _setup_commands() -> Iterator[Command]:
        yield from (
            SetRngSeed(
                rng_seed=c.options.rng_seed,
            ),
            SetPipelineCreateDir(
                is_create_dir=c.directory.is_enabled,
            ),
            CreateTransferFn(
                transfermode=c.options.transfer_mode,
            ),
            CreateFilenameFn(
                template=c.filename.template,
                is_enabled=c.filename.is_enabled,
            ),
            CreateDestDirs(
                dir_count=c.directory.count,
                directory_dest=c.dest,
                directory_name=c.directory.name,
                directory_create_is_enabled=c.directory.is_enabled,
                filecount_static=c.filecount.count,
                filecount_randrange=(c.filecount.rand_min, c.filecount.rand_max),
                filecount_rand_is_enabled=c.filecount.is_rand_enabled,
            ),
            CreateWalkerFn(
                root=c.root,
                should_follow_symlink=c.options.should_follow_symlink,
            ),
        )
        text_specs = [
            (c.dirname, FilterName.DIRNAME, ReStrFmt.DIRECTORY),
            (c.keyword, FilterName.KEYWORD, ReStrFmt.KEYWORD),
            (c.extension, FilterName.EXTENSION, ReStrFmt.EXTENSION),
        ]
        for model, name, re_fmt in text_specs:
            yield CreateTextFilterFn(
                name=name,
                text=model.text,
                re_fmt=re_fmt,
                is_enabled=model.is_enabled,
                should_include=model.should_include,
            )
        range_specs = [
            (c.filesize, FilterName.FILESIZE, SIZE_MAP),
            (c.duration, FilterName.DURATION, TIME_MAP),
        ]
        for model, name, unit_map in range_specs:
            mul = unit_map.get(model.unit, 1.0)
            yield CreateRangeFilterFn(
                name=name,
                minimum=model.minimum * mul,
                maximum=model.maximum * mul,
                is_enabled=model.is_enabled,
            )
        yield CreateFilefilterFn()
        yield CreateTransferJob(
            root=c.root,
            max_per_dir=c.options.max_per_dir,
            unique_files_only=c.options.is_create_unique_dirs,
        )

    for cmd in _setup_commands():
        bus.handle(cmd)


@dataclass(slots=True)
class FSPachinkoBootstrapper:
    """Bootstrapper for the FSPachinko application."""

    collector: CompositeEventCollector = field(default_factory=CompositeEventCollector)
    pipeline: AbstractPipeline = field(default_factory=TransferPipeline)
    fst_uow: AbstractTransferUnitOfWork = field(default_factory=TransferUnitOfWork)
    cfg_uow: AbstractConfigUnitOfWork = field(default_factory=JSONConfigUnitOfWork)
    log_fn: Callable = logger.info
    rng_seed_fn: Callable = seed

    @classmethod
    def bootstrap(cls, *args: Any, **kwargs: Any) -> tuple[MessageBus, AbstractPipeline]:
        """Bootstrap the application and return the message bus."""
        b = cls(*args, **kwargs)
        b.collector.register_emitter(b.fst_uow)
        return MessageBus(
            collector=b.collector,
            event_handlers=b.get_event_handlers(),
            command_handlers=b.get_command_handlers(),
        ), b.pipeline

    def get_event_handlers(self) -> dict[type[Event], list[Callable]]:
        """Get the event handlers."""
        log_fn = self.log_fn
        return {
            FileTransferred: [FileTransferredHandler(log_fn=log_fn)],
            DirectoryStarted: [DirectoryStartedHandler(log_fn=log_fn)],
            DirectoryTransferred: [DirectoryTransferredHandler(log_fn=log_fn)],
        }

    def get_command_handlers(self) -> dict[type[Command], Callable]:
        """Get the command handlers."""
        fst_uow, cfg_uow, pipeline, rng_seed_fn = self.fst_uow, self.cfg_uow, self.pipeline, self.rng_seed_fn
        return {
            RunTransferJob: RunTransferJobHandler(uow=fst_uow, pipeline=pipeline),
            CreateTransferJob: CreateTransferJobHandler(uow=fst_uow),
            ProcessDirectory: ProcessDirectoryHandler(uow=fst_uow, pipeline=pipeline),
            StopProcess: StopProcessHandler(uow=fst_uow),
            SetRngSeed: SetRngSeedHandler(rng_seed_fn=rng_seed_fn),
            SetPipelineCreateDir: SetPipelineCreateDirHandler(pipeline=pipeline),
            CreateTransferFn: CreateTransferFnHandler(pipeline=pipeline),
            CreateFilenameFn: CreateFilenameFnHandler(pipeline=pipeline),
            CreateDestDirs: CreateDestDirsHandler(pipeline=pipeline),
            CreateWalkerFn: CreateWalkerFnHandler(pipeline=pipeline),
            CreateTextFilterFn: CreateTextFilterFnHandler(pipeline=pipeline),
            CreateRangeFilterFn: CreateRangeFilterFnHandler(pipeline=pipeline),
            CreateFilefilterFn: CreateFilefilterFnHandler(pipeline=pipeline),
            SaveProfile: SaveProfileHandler(uow=cfg_uow),
        }
