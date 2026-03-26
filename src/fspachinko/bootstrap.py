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
from .config import ConfigBootstrapper
from .configuration.uow import AbstractConfigUnitOfWork, JSONConfigUnitOfWork
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
    SaveConfiguration,
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
    from collections.abc import Callable

    from .configuration.model import ConfigModel


logger = logging.getLogger(__name__)


def configure_bus(bus: MessageBus, config: ConfigModel) -> None:
    """Configure the message bus with commands based on the configuration."""
    configurator = ConfigBootstrapper(config=config)
    for cmd in configurator.translate():
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

    def __post_init__(self) -> None:
        """Post-initialization to set up the message bus."""
        self.collector.register_emitter(self.fst_uow)

    @classmethod
    def bootstrap(cls, *args: Any, **kwargs: Any) -> MessageBus:
        """Bootstrap the application and return the message bus."""
        b = cls(*args, **kwargs)
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
            CreateFilenameFn: CreateFilenameFnHandler(
                pipeline=pipeline,
                template_filenamer=TemplateFilenamer,
            ),
            CreateDestDirs: CreateDestDirsHandler(
                pipeline=pipeline,
                get_unique_path=get_unique_path,
                randcount_fn=randint,
                make_directory=mkdir,
                get_existing_directories=get_existing_directories,
                join_path=join,
            ),
            CreateWalkerFn: CreateWalkerFnHandler(
                pipeline=pipeline,
                walker=FSWalker,
            ),
            CreateTextFilterFn: CreateTextFilterFnHandler(
                pipeline=pipeline,
                get_text_patterns=get_text_patterns,
            ),
            CreateRangeFilterFn: CreateRangeFilterFnHandler(pipeline=pipeline),
            CreateFilefilterFn: CreateFilefilterFnHandler(
                pipeline=pipeline,
                get_duration=get_duration,
            ),
            SaveConfiguration: SaveProfileHandler(uow=cfg_uow),
        }
