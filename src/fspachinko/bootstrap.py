"""Builder module for core functionality."""

import logging
from random import seed
from typing import TYPE_CHECKING

from fspachinko.domain.commands import CreateTransferJob

from .adapters.pipeline import AbstractPipeline, TransferPipeline
from .domain.commands import (
    CreateDirnameFn,
    CreateFilecountFn,
    CreateFilefilterFn,
    CreateFilenameFn,
    CreateRangeFilterFn,
    CreateTextFilterFn,
    CreateTransferFn,
    CreateWalkerFn,
    ProcessDirectory,
    StopProcess,
)
from .domain.events import DirectoryTransferred, FileTransferred
from .service.handlers import (
    CreateDirnameFnHandler,
    CreateFilecountFnHandler,
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
    StopProcessHandler,
)
from .service.messagebus import MessageBus
from .service.uow import AbstractUnitOfWork, FileSystemUnitOfWork

if TYPE_CHECKING:
    from collections.abc import Callable

    from .configuration.model import ConfigModel

logger = logging.getLogger(__name__)


def bootstrap(
    m: ConfigModel,
    pipeline: AbstractPipeline | None = None,
    log_fn: Callable | None = None,
    fs_uow: AbstractUnitOfWork | None = None,
) -> MessageBus:
    """Bootstrap the application and return the message bus."""
    seed(m.options.rng_seed)
    if pipeline is None:
        pipeline = TransferPipeline(is_create_dir=m.directory.is_enabled)
    if log_fn is None:
        log_fn = logger.info
    if fs_uow is None and isinstance(pipeline, TransferPipeline):
        fs_uow = FileSystemUnitOfWork(pipeline=pipeline)
    if not isinstance(fs_uow, FileSystemUnitOfWork):
        msg = "Unit of Work must be provided if pipeline is not a TransferPipeline."
        raise TypeError(msg)
    uows = {
        "fs": fs_uow,
    }
    event_handlers = {
        FileTransferred: [FileTransferredHandler(log_fn=log_fn)],
        DirectoryTransferred: [DirectoryTransferredHandler(log_fn=log_fn)],
    }
    command_handlers = {
        CreateTransferJob: CreateTransferJobHandler(uow=uows["fs"]),
        ProcessDirectory: ProcessDirectoryHandler(uow=uows["fs"]),
        StopProcess: StopProcessHandler(uow=uows["fs"]),
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
