"""Builder module for core functionality."""

import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from fspachinko.adapters.filenamer import TemplateFilenamer
from fspachinko.adapters.filesystem import AbstractFilesystem, Filesystem
from fspachinko.adapters.fswalker import FSWalker
from fspachinko.adapters.loggers import AbstractLogger, AppLogger
from fspachinko.adapters.media import AbstractDurationFnManager, DurationFnManager
from fspachinko.adapters.pipeline import AbstractPipeline, TransferPipeline
from fspachinko.adapters.transfer import FileTransferFnManager
from fspachinko.config import ConfigToFileFilter, ConfigToPipeline
from fspachinko.configuration.uow import AbstractConfigUnitOfWork, JSONConfigUnitOfWork
from fspachinko.domain.commands import (
    Command,
    CreateTransferJob,
    ProcessDirectory,
    RunTransferJob,
    SaveConfiguration,
    StopProcess,
)
from fspachinko.domain.events import DirectoryStarted, DirectoryTransferred, Event, FileTransferred
from fspachinko.helpers import get_report, get_status, get_text_patterns
from fspachinko.service.eventcollector import CompositeEventCollector
from fspachinko.service.handlers import (
    CreateTransferJobHandler,
    DirectoryStartedHandler,
    DirectoryTransferredHandler,
    FileTransferredHandler,
    ProcessDirectoryHandler,
    RunTransferJobHandler,
    SaveProfileHandler,
    StopProcessHandler,
)
from fspachinko.service.messagebus import MessageBus
from fspachinko.service.uow import AbstractTransferUnitOfWork, TransferUnitOfWork

if TYPE_CHECKING:
    from collections.abc import Callable

    from fspachinko.adapters.transfer import AbstractTransferFnManager
    from fspachinko.configuration.model import ConfigModel


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

    config_to_pipeline: ConfigToPipeline = field(init=False)

    def __post_init__(self) -> None:
        """Post-initialization to set up the message bus."""
        self.collector.register_emitter(self.fst_uow)
        self.config_to_pipeline = ConfigToPipeline(
            pipeline=self.pipeline,
            filesystem=self.filesystem,
            rng_seed_fn=self.rng_seed_fn,
            transfer_fn_manager=self.transfer_fn_manager,
            template_filenamer=TemplateFilenamer,
            walker=FSWalker,
            randcount_fn=random.randint,
            get_text_patterns=get_text_patterns,
            config_to_file_filter=ConfigToFileFilter(
                get_text_patterns=get_text_patterns,
                get_duration=self.duration_fn_manager.get_duration,
            ),
        )

    def bootstrap(self) -> MessageBus:
        """Bootstrap the application and return the message bus."""
        return MessageBus(
            collector=self.collector,
            event_handlers=self.get_event_handlers(),
            command_handlers=self.get_command_handlers(),
            logger=self.logger,
        )

    def configure_pipeline_for_run(self, c: ConfigModel) -> None:
        """Configure the pipeline based on the configuration model."""
        self.config_to_pipeline.apply(c)
        self.fst_uow.transfer_fn = self.pipeline.transfer_fn

    def get_event_handlers(self) -> dict[type[Event], list[Callable]]:
        """Get the event handlers."""
        return {
            FileTransferred: [
                FileTransferredHandler(
                    logger=self.logger,
                ),
            ],
            DirectoryStarted: [
                DirectoryStartedHandler(
                    logger=self.logger,
                ),
            ],
            DirectoryTransferred: [
                DirectoryTransferredHandler(
                    get_status=get_status,
                    get_report=get_report,
                    filesystem=self.filesystem,
                    logger=self.logger,
                ),
            ],
        }

    def get_command_handlers(self) -> dict[type[Command], Callable]:
        """Get the command handlers."""
        return {
            RunTransferJob: RunTransferJobHandler(
                uow=self.fst_uow,
                pipeline=self.pipeline,
            ),
            CreateTransferJob: CreateTransferJobHandler(
                uow=self.fst_uow,
            ),
            ProcessDirectory: ProcessDirectoryHandler(
                uow=self.fst_uow,
                pipeline=self.pipeline,
            ),
            StopProcess: StopProcessHandler(
                uow=self.fst_uow,
            ),
            SaveConfiguration: SaveProfileHandler(
                uow=self.cfg_uow,
            ),
        }
