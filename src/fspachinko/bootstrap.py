"""Builder module for core functionality."""

import random
from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from fspachinko.adapters.duration import duration_fn_factory
from fspachinko.adapters.filenamer import TemplateFilenamer
from fspachinko.adapters.filesystem import AbstractFilesystem, Filesystem
from fspachinko.adapters.fswalker import FSWalker
from fspachinko.adapters.loggers import AbstractLogger, AppLogger
from fspachinko.adapters.pipeline import AbstractPipeline, TransferPipeline
from fspachinko.adapters.transfer import available_transfer_fn_factory
from fspachinko.config import ConfigModelBootstrapper, ConfigToFileFilter
from fspachinko.datapaths import ensure_data_paths
from fspachinko.domain.commands import Command, RunTransferJob, SaveConfiguration, StopProcess
from fspachinko.domain.events import DirectoryStarted, DirectoryTransferred, Event, FileTransferred
from fspachinko.domain.model import TransferJob
from fspachinko.helpers import get_report, get_status
from fspachinko.service.eventcollector import CompositeEventCollector
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

    collector: CompositeEventCollector = field(default_factory=CompositeEventCollector)
    filesystem: AbstractFilesystem = field(default_factory=Filesystem)
    pipeline: AbstractPipeline = field(default_factory=TransferPipeline)
    logger: AbstractLogger = field(default_factory=AppLogger)
    available_transfer_fns: dict[str, Callable] = field(default_factory=available_transfer_fn_factory)
    duration_fn: Callable[[str], float] = field(default_factory=duration_fn_factory)
    job: TransferJob = field(default_factory=TransferJob)
    rng: random.Random = field(default_factory=random.Random)
    inputs: deque[tuple[str, int, bool]] = field(default_factory=deque)

    config_model_bootstrapper: ConfigModelBootstrapper = field(init=False)

    def __post_init__(self) -> None:
        """Post-initialization to set up the message bus."""
        ensure_data_paths()
        self.collector.register_emitter(self.job)
        self.config_model_bootstrapper = ConfigModelBootstrapper(
            pipeline=self.pipeline,
            filesystem=self.filesystem,
            rng=self.rng,
            available_transfer_fns=self.available_transfer_fns,
            template_filenamer=TemplateFilenamer,
            walker=FSWalker,
            config_to_file_filter=ConfigToFileFilter(
                get_duration=self.duration_fn,
            ),
        )

    def configure_pipeline_for_run(self, c: ConfigModel) -> None:
        """Configure the pipeline based on the configuration model."""
        self.config_model_bootstrapper.apply(c)
        self.inputs.extend(self.config_model_bootstrapper.build_inputs(c))

    def build_message_bus(self) -> MessageBus:
        """Bootstrap the application and return the message bus."""
        return MessageBus(
            collector=self.collector,
            command_handlers=self.get_command_handlers(),
            event_handlers=self.get_event_handlers(),
            logger=self.logger,
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
                    get_status=get_status,
                    get_report=get_report,
                    filesystem=self.filesystem,
                    logger=self.logger,
                ),
            ],
        }
