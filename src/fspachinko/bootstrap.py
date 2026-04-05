"""Builder module for core functionality."""

import random
from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from fspachinko.adapters.duration import duration_fn_factory
from fspachinko.adapters.filenamer import AbstractFilenamer, TemplateFilenamer
from fspachinko.adapters.filesystem import AbstractFilesystem, Filesystem
from fspachinko.adapters.fswalker import AbstractFSWalker, FSWalker
from fspachinko.adapters.loggers import AbstractLogger, AppLogger
from fspachinko.adapters.pipeline import AbstractPipeline, TransferPipeline
from fspachinko.adapters.transfer import available_transfer_fn_factory
from fspachinko.config import ConfigModelBootstrapper, ConfigToFileFilter
from fspachinko.datapaths import ensure_data_paths
from fspachinko.domain.commands import Command, RunTransferJob, SaveConfiguration, StopProcess
from fspachinko.domain.events import DirectoryStarted, DirectoryTransferred, Event, FileTransferred
from fspachinko.domain.model import TransferJob
from fspachinko.helpers import ReportWriter
from fspachinko.service.handlers import (
    DirectoryStartedHandler,
    DirectoryTransferredHandler,
    FileTransferredHandler,
    RunTransferJobHandler,
    SaveProfileHandler,
    StopProcessHandler,
)
from fspachinko.service.messagebus import MessageBus

if TYPE_CHECKING:
    from collections.abc import Callable

    from fspachinko.config import ConfigModel


@dataclass(slots=True)
class FSPachinkoBootstrapper:
    """Bootstrapper for the FSPachinko application."""

    filesystem: AbstractFilesystem = field(default_factory=Filesystem)
    pipeline: AbstractPipeline = field(default_factory=TransferPipeline)
    logger: AbstractLogger = field(default_factory=AppLogger)
    available_transfer_fns: dict[str, Callable] = field(default_factory=available_transfer_fn_factory)
    duration_fn: Callable[[str], float] = field(default_factory=duration_fn_factory)
    job: TransferJob = field(default_factory=TransferJob)
    rng: random.Random = field(default_factory=random.Random)
    inputs: deque[tuple[str, int, bool]] = field(default_factory=deque)
    template_filenamer: type[AbstractFilenamer] = TemplateFilenamer
    walker: type[AbstractFSWalker] = FSWalker
    reporter: type[ReportWriter] = ReportWriter
    config_model_bootstrapper: ConfigModelBootstrapper = field(init=False)

    def __post_init__(self) -> None:
        """Post-initialization to set up the message bus."""
        ensure_data_paths()
        self.config_model_bootstrapper = ConfigModelBootstrapper(
            pipeline=self.pipeline,
            filesystem=self.filesystem,
            rng=self.rng,
            available_transfer_fns=self.available_transfer_fns,
            template_filenamer=self.template_filenamer,
            walker=self.walker,
            config_to_file_filter=ConfigToFileFilter(get_duration=self.duration_fn),
        )

    def configure_pipeline_for_run(self, c: ConfigModel) -> None:
        """Configure the pipeline based on the configuration model."""
        self.config_model_bootstrapper.apply(c)
        self.inputs.clear()
        self.inputs.extend(self.config_model_bootstrapper.build_inputs(c))

    def build_message_bus(self) -> MessageBus:
        """Bootstrap the application and return the message bus."""
        return MessageBus(
            command_handlers=self.get_command_handlers(),
            event_handlers=self.get_event_handlers(),
        )

    def get_command_handlers(self) -> dict[type[Command], Callable]:
        """Get the command handlers."""
        return {
            RunTransferJob: RunTransferJobHandler(
                job=self.job,
                inputs=self.inputs,
                filesystem=self.filesystem,
                pipeline=self.pipeline,
            ),
            StopProcess: StopProcessHandler(
                job=self.job,
            ),
            SaveConfiguration: SaveProfileHandler(
                filesystem=self.filesystem,
            ),
        }

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
                    filesystem=self.filesystem,
                    logger=self.logger,
                    reporter=self.reporter,
                ),
            ],
        }
