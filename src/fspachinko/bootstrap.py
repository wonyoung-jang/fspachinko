"""Builder module for core functionality."""

import logging
from random import seed
from typing import TYPE_CHECKING

from fspachinko.domain.commands import CreateFilefilterFn, CreateRangeFilterFn, CreateTextFilterFn
from fspachinko.service.handlers import CreateFilefilterFnHandler, CreateRangeFilterFnHandler, CreateTextFilterFnHandler

from .adapters.pipeline import AbstractPipeline, TransferPipeline
from .domain.commands import (
    CreateDirnameFn,
    CreateFilecountFn,
    CreateFilenameFn,
    CreateTransferFn,
    CreateWalkerFn,
    ProcessDirectory,
    StopProcess,
)
from .domain.events import DirectoryTransferred, FileTransferred
from .domain.model import DiversityQuota, TransferJob
from .service.handlers import (
    CreateDirnameFnHandler,
    CreateFilecountFnHandler,
    CreateFilenameFnHandler,
    CreateTransferFnHandler,
    CreateWalkerFnHandler,
    DirectoryTransferredHandler,
    FileTransferredHandler,
    ProcessDirectoryHandler,
    StopProcessHandler,
)
from .service.messagebus import MessageBus
from .service.uow import AbstractUnitOfWork, FileSystemUnitOfWork

if TYPE_CHECKING:
    from .configuration.model import ConfigModel

logger = logging.getLogger(__name__)


def bootstrap(
    m: ConfigModel,
    pipeline: AbstractPipeline,
    fs_uow: AbstractUnitOfWork | None = None,
) -> MessageBus:
    """Bootstrap the application and return the message bus."""
    seed(m.options.rng_seed)
    job = TransferJob(
        quota=DiversityQuota(
            root=m.root,
            max_per_dir=m.options.max_per_dir,
            unique_files_only=m.options.is_create_unique_dirs,
        )
    )
    if fs_uow is None and isinstance(pipeline, TransferPipeline):
        fs_uow = FileSystemUnitOfWork(pipeline=pipeline, job=job)
    if fs_uow is None or not isinstance(fs_uow, FileSystemUnitOfWork):
        msg = "Unit of Work must be provided if pipeline is not a TransferPipeline."
        raise ValueError(msg)
    uows = {
        "fs": fs_uow,
    }
    event_handlers = {
        FileTransferred: [FileTransferredHandler(call=logger.info)],
        DirectoryTransferred: [DirectoryTransferredHandler(call=logger.info)],
    }
    command_handlers = {
        ProcessDirectory: ProcessDirectoryHandler(uow=fs_uow),
        StopProcess: StopProcessHandler(uow=fs_uow),
        CreateTransferFn: CreateTransferFnHandler(pipeline=pipeline),
        CreateFilenameFn: CreateFilenameFnHandler(pipeline=pipeline),
        CreateFilecountFn: CreateFilecountFnHandler(pipeline=pipeline),
        CreateDirnameFn: CreateDirnameFnHandler(pipeline=pipeline),
        CreateWalkerFn: CreateWalkerFnHandler(pipeline=pipeline),
        CreateTextFilterFn: CreateTextFilterFnHandler(pipeline=pipeline),
        CreateRangeFilterFn: CreateRangeFilterFnHandler(pipeline=pipeline),
        CreateFilefilterFn: CreateFilefilterFnHandler(pipeline=pipeline),
    }
    return MessageBus(
        uows=uows,
        event_handlers=event_handlers,
        command_handlers=command_handlers,
    )
