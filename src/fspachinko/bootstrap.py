"""Builder module for core functionality."""

import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from fspachinko.adapters.cache import SQLiteMetadataCache
from fspachinko.adapters.loggers import AbstractLogger, AppLogger
from fspachinko.adapters.pipeline import AbstractPipeline, TransferPipeline
from fspachinko.adapters.system import (
    AbstractFilenamer,
    AbstractFilesystem,
    AbstractFSWalker,
    Filesystem,
    FSWalker,
    TemplateFilenamer,
    get_transfer_fn,
)
from fspachinko.config import ConfigManager, ConfigModelBootstrapper
from fspachinko.datapaths import ensure_data_paths, get_cache_path
from fspachinko.domain.commands import Command, ConfigurePipeline, RunTransferJob, SaveConfiguration, StopProcess
from fspachinko.domain.events import (
    DirectoryStarted,
    DirectoryTransferred,
    Event,
    FileTransferred,
    PipelineConfigured,
    RunFinished,
    RunStarted,
)
from fspachinko.domain.model import TransferJob
from fspachinko.fp import Fp
from fspachinko.helpers import ReportWriter
from fspachinko.service.handlers import (
    ConfigurePipelineHandler,
    DirectoryStartedHandler,
    DirectoryTransferredHandler,
    FileTransferredHandler,
    PipelineConfiguredHandler,
    RunFinishedHandler,
    RunStartedHandler,
    RunTransferJobHandler,
    SaveConfigurationHandler,
    StopProcessHandler,
)
from fspachinko.service.messagebus import MessageBus

if TYPE_CHECKING:
    from collections.abc import Callable

ensure_data_paths()


@dataclass(slots=True)
class Bootstrapper:
    """Bootstrapper for the FSPachinko application."""

    fs: AbstractFilesystem = field(default_factory=Filesystem)
    pipeline: AbstractPipeline = field(default_factory=TransferPipeline)
    logger: AbstractLogger = field(default_factory=AppLogger)
    transfer_fn_getter: Callable[[str], Callable[[str, str], None]] = get_transfer_fn
    job: TransferJob = field(default_factory=TransferJob)
    rng: random.Random = field(default_factory=random.Random)
    filenamer_cls: type[AbstractFilenamer] = TemplateFilenamer
    walker_cls: type[AbstractFSWalker] = FSWalker
    reporter_cls: type[ReportWriter] = ReportWriter
    config_manager: ConfigManager = field(init=False)

    def __post_init__(self) -> None:
        """Post-initialization to set up the message bus."""
        self.config_manager = ConfigManager(fs=self.fs)
        self.pipeline.cache = SQLiteMetadataCache(get_cache_path(Fp.Path.CACHE))

    def build_message_bus(self) -> MessageBus:
        """Bootstrap the application and return the message bus."""
        bus = MessageBus()
        bus.command_handlers.update(self.get_command_handlers())
        bus.event_handlers.update(self.get_event_handlers())
        return bus

    def get_command_handlers(self) -> dict[type[Command], Callable]:
        """Get the command handlers."""
        return {
            ConfigurePipeline: ConfigurePipelineHandler(
                pipeline=self.pipeline,
                configurator=ConfigModelBootstrapper(
                    fs=self.fs,
                    get_transfer_fn=self.transfer_fn_getter,
                    template_filenamer=self.filenamer_cls,
                    walker=self.walker_cls,
                    rng=self.rng,
                ),
            ),
            RunTransferJob: RunTransferJobHandler(job=self.job, fs=self.fs, pipeline=self.pipeline),
            StopProcess: StopProcessHandler(job=self.job),
            SaveConfiguration: SaveConfigurationHandler(fs=self.fs),
        }

    def get_event_handlers(self) -> dict[type[Event], list[Callable]]:
        """Get the event handlers."""
        return {
            PipelineConfigured: [PipelineConfiguredHandler(logger=self.logger)],
            RunStarted: [RunStartedHandler(logger=self.logger)],
            FileTransferred: [FileTransferredHandler(logger=self.logger)],
            DirectoryStarted: [DirectoryStartedHandler(logger=self.logger)],
            DirectoryTransferred: [
                DirectoryTransferredHandler(fs=self.fs, logger=self.logger, reporter=self.reporter_cls)
            ],
            RunFinished: [RunFinishedHandler(logger=self.logger)],
        }
