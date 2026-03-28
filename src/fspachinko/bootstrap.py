"""Builder module for core functionality."""

import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .adapters.filenamer import TemplateFilenamer
from .adapters.filesystem import AbstractFilesystem, Filesystem
from .adapters.fswalker import FSWalker
from .adapters.loggers import AbstractLogger, AppLogger
from .adapters.media import AbstractDurationFnManager, DurationFnManager
from .adapters.pipeline import AbstractPipeline, TransferPipeline
from .adapters.transfer import FileTransferFnManager
from .config import ConfigToFileFilter
from .configuration.uow import AbstractConfigUnitOfWork, JSONConfigUnitOfWork
from .domain.commands import (
    BootstrapConfig,
    Command,
    CreateTransferJob,
    ProcessDirectory,
    RunTransferJob,
    SaveConfiguration,
    StopProcess,
)
from .domain.events import DirectoryStarted, DirectoryTransferred, Event, FileTransferred
from .helpers import get_report, get_status, get_text_patterns
from .service.eventcollector import CompositeEventCollector
from .service.handlers import (
    BootstrapConfigHandler,
    CreateTransferJobHandler,
    DirectoryStartedHandler,
    DirectoryTransferredHandler,
    FileTransferredHandler,
    ProcessDirectoryHandler,
    RunTransferJobHandler,
    SaveProfileHandler,
    StopProcessHandler,
)
from .service.messagebus import MessageBus
from .service.uow import AbstractTransferUnitOfWork, TransferUnitOfWork

if TYPE_CHECKING:
    from collections.abc import Callable

    from .adapters.transfer import AbstractTransferFnManager


@dataclass(slots=True)
class FSPachinkoBootstrapper:
    """Bootstrapper for the FSPachinko application."""

    collector: CompositeEventCollector = field(default_factory=CompositeEventCollector)
    filesystem: AbstractFilesystem = field(default_factory=Filesystem)
    pipeline: AbstractPipeline = field(default_factory=TransferPipeline)
    fst_uow: AbstractTransferUnitOfWork = field(default_factory=TransferUnitOfWork)
    cfg_uow: AbstractConfigUnitOfWork = field(default_factory=JSONConfigUnitOfWork)
    logger: AbstractLogger = field(default_factory=AppLogger)
    transfer_fn_manager: AbstractTransferFnManager = field(default_factory=FileTransferFnManager)
    duration_fn_manager: AbstractDurationFnManager = field(default_factory=DurationFnManager)
    rng_seed_fn: Callable = random.seed

    def __post_init__(self) -> None:
        """Post-initialization to set up the message bus."""
        self.collector.register_emitter(self.fst_uow)
        self.pipeline.filesystem = self.filesystem

    def bootstrap(self) -> MessageBus:
        """Bootstrap the application and return the message bus."""
        return MessageBus(
            collector=self.collector,
            event_handlers=self.get_event_handlers(),
            command_handlers=self.get_command_handlers(),
            logger=self.logger,
        )

    def get_event_handlers(self) -> dict[type[Event], list[Callable]]:
        """Get the event handlers."""
        return {
            FileTransferred: [
                FileTransferredHandler(logger=self.logger),
            ],
            DirectoryStarted: [
                DirectoryStartedHandler(logger=self.logger),
            ],
            DirectoryTransferred: [
                DirectoryTransferredHandler(
                    get_status=get_status,
                    get_report=get_report,
                    remove_directory=self.filesystem.remove_directory,
                    logger=self.logger,
                )
            ],
        }

    def get_command_handlers(self) -> dict[type[Command], Callable]:
        """Get the command handlers."""
        fst_uow, pipeline = self.fst_uow, self.pipeline
        return {
            RunTransferJob: RunTransferJobHandler(
                uow=fst_uow,
                pipeline=pipeline,
            ),
            CreateTransferJob: CreateTransferJobHandler(uow=fst_uow),
            ProcessDirectory: ProcessDirectoryHandler(
                uow=fst_uow,
                pipeline=pipeline,
            ),
            StopProcess: StopProcessHandler(uow=fst_uow),
            SaveConfiguration: SaveProfileHandler(uow=self.cfg_uow),
            BootstrapConfig: BootstrapConfigHandler(
                pipeline=pipeline,
                filesystem=self.filesystem,
                rng_seed_fn=self.rng_seed_fn,
                transfer_fn_manager=self.transfer_fn_manager.get_transfer_fn,
                get_duration=self.duration_fn_manager.get_duration,
                template_filenamer=TemplateFilenamer,
                walker=FSWalker,
                config_to_file_filter=ConfigToFileFilter,
                randcount_fn=random.randint,
                get_text_patterns=get_text_patterns,
            ),
        }
