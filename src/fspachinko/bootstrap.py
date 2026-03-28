"""Builder module for core functionality."""

import logging
import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .adapters.filenamer import TemplateFilenamer
from .adapters.filesystem import AbstractFilesystem, Filesystem
from .adapters.fswalker import FSWalker
from .adapters.loggers import add_dest_log_filehandler, remove_dest_log_filehandler
from .adapters.media import get_duration
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


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class FSPachinkoBootstrapper:
    """Bootstrapper for the FSPachinko application."""

    collector: CompositeEventCollector = field(default_factory=CompositeEventCollector)
    filesystem: AbstractFilesystem = field(default_factory=Filesystem)
    pipeline: AbstractPipeline = field(default_factory=TransferPipeline)
    fst_uow: AbstractTransferUnitOfWork = field(default_factory=TransferUnitOfWork)
    cfg_uow: AbstractConfigUnitOfWork = field(default_factory=JSONConfigUnitOfWork)
    log_fn: Callable = logger.info
    rng_seed_fn: Callable = random.seed

    def __post_init__(self) -> None:
        """Post-initialization to set up the message bus."""
        self.collector.register_emitter(self.fst_uow)
        self.pipeline.filesystem = self.filesystem

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
                    get_status=get_status,
                    get_report=get_report,
                    remove_log_file=remove_dest_log_filehandler,
                    remove_directory=self.filesystem.remove_directory,
                )
            ],
        }

    def get_command_handlers(self) -> dict[type[Command], Callable]:
        """Get the command handlers."""
        fst_uow, cfg_uow, pipeline, filesystem, rng_seed_fn = (
            self.fst_uow,
            self.cfg_uow,
            self.pipeline,
            self.filesystem,
            self.rng_seed_fn,
        )
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
            SaveConfiguration: SaveProfileHandler(uow=cfg_uow),
            BootstrapConfig: BootstrapConfigHandler(
                pipeline=pipeline,
                filesystem=filesystem,
                rng_seed_fn=rng_seed_fn,
                transfer_fn_getter=FileTransferFnManager(),
                template_filenamer=TemplateFilenamer,
                walker=FSWalker,
                randcount_fn=random.randint,
                get_text_patterns=get_text_patterns,
                get_duration=get_duration,
                config_to_file_filter=ConfigToFileFilter,
            ),
        }
