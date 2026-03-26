"""Builder module for core functionality."""

import logging
from dataclasses import dataclass, field
from os import mkdir
from os.path import join
from random import randint, seed
from typing import TYPE_CHECKING, Any

from .adapters.filenamer import TemplateFilenamer
from .adapters.filesystemport import get_existing_directories, get_unique_path, remove_directory
from .adapters.fswalker import FSWalker
from .adapters.loggers import add_dest_log_filehandler, remove_dest_log_filehandler
from .adapters.media import get_duration
from .adapters.pipeline import AbstractPipeline, TransferPipeline
from .adapters.transfer import FileTransferFnManager
from .configuration.uow import AbstractConfigUnitOfWork, JSONConfigUnitOfWork
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
    RunTransferJob,
    SaveProfile,
    SetPipelineCreateDir,
    SetRngSeed,
    StopProcess,
)
from .domain.events import DirectoryStarted, DirectoryTransferred, Event, FileTransferred
from .helpers import get_report, get_status, get_text_patterns
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
    DirectoryStartedHandler,
    DirectoryTransferredHandler,
    FileTransferredHandler,
    ProcessDirectoryHandler,
    RunTransferJobHandler,
    SaveProfileHandler,
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


def bootstrap(*args: Any, **kwargs: Any) -> MessageBus:
    """Bootstrap the application and return the message bus."""
    return FSPachinkoBootstrapper.bootstrap(*args, **kwargs)


def setup_bus_commands(c: ConfigModel) -> Iterator[Command]:
    """Bootstrap the application."""
    yield from (
        CreateTransferJob(
            root=c.root,
            max_per_dir=c.options.max_per_dir,
            unique_files_only=c.options.is_create_unique_dirs,
        ),
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
    def bootstrap(cls, *args: Any, **kwargs: Any) -> MessageBus:
        """Bootstrap the application and return the message bus."""
        b = cls(*args, **kwargs)
        b.collector.register_emitter(b.fst_uow)
        return MessageBus(
            collector=b.collector,
            event_handlers=b.get_event_handlers(),
            command_handlers=b.get_command_handlers(),
        )

    def get_event_handlers(self) -> dict[type[Event], list[Callable]]:
        """Get the event handlers."""
        log_fn = self.log_fn
        return {
            FileTransferred: [FileTransferredHandler(log_fn=log_fn)],
            DirectoryStarted: [
                DirectoryStartedHandler(
                    log_fn=log_fn,
                    add_log_file=add_dest_log_filehandler,
                )
            ],
            DirectoryTransferred: [
                DirectoryTransferredHandler(
                    log_fn=log_fn,
                    remove_log_file=remove_dest_log_filehandler,
                    get_status=get_status,
                    get_report=get_report,
                )
            ],
        }

    def get_command_handlers(self) -> dict[type[Command], Callable]:
        """Get the command handlers."""
        fst_uow, cfg_uow, pipeline, rng_seed_fn = self.fst_uow, self.cfg_uow, self.pipeline, self.rng_seed_fn
        return {
            RunTransferJob: RunTransferJobHandler(
                uow=fst_uow,
                pipeline=pipeline,
                remove_directory=remove_directory,
            ),
            CreateTransferJob: CreateTransferJobHandler(uow=fst_uow),
            ProcessDirectory: ProcessDirectoryHandler(
                uow=fst_uow,
                pipeline=pipeline,
                remove_directory=remove_directory,
            ),
            StopProcess: StopProcessHandler(uow=fst_uow),
            SetRngSeed: SetRngSeedHandler(rng_seed_fn=rng_seed_fn),
            SetPipelineCreateDir: SetPipelineCreateDirHandler(pipeline=pipeline),
            CreateTransferFn: CreateTransferFnHandler(
                pipeline=pipeline,
                transfer_fn_getter=FileTransferFnManager().get,
            ),
            CreateFilenameFn: CreateFilenameFnHandler(pipeline=pipeline, template_filenamer=TemplateFilenamer),
            CreateDestDirs: CreateDestDirsHandler(
                uow=fst_uow,
                get_unique_path=get_unique_path,
                randcount_fn=randint,
                make_directory=mkdir,
                get_existing_directories=get_existing_directories,
                join_path=join,
            ),
            CreateWalkerFn: CreateWalkerFnHandler(pipeline=pipeline, walker=FSWalker),
            CreateTextFilterFn: CreateTextFilterFnHandler(pipeline=pipeline, get_text_patterns=get_text_patterns),
            CreateRangeFilterFn: CreateRangeFilterFnHandler(pipeline=pipeline),
            CreateFilefilterFn: CreateFilefilterFnHandler(pipeline=pipeline, get_duration=get_duration),
            SaveProfile: SaveProfileHandler(uow=cfg_uow),
        }
