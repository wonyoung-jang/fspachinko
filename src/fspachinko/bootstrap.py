"""Builder module for core functionality."""

import logging
from random import seed
from typing import TYPE_CHECKING

from .adapters import ConcreteLoggingPort
from .adapters.filesystemport import ConcreteFilesystemPort
from .adapters.pipeline import AbstractPipeline, TransferPipeline
from .domain.model import DiversityQuota, TransferJob
from .service.handlers import (
    COMMAND_HANDLERS,
    EVENT_HANDLERS,
    get_dirname_fn,
    get_filecount_fn,
    get_filefilter_fn,
    get_filenamer_fn,
    get_transfer_fn,
    get_walker_fn,
)
from .service.messagebus import MessageBus
from .service.uow import AbstractUnitOfWork, FileSystemUnitOfWork

if TYPE_CHECKING:
    from .config import ConfigModel


logger = logging.getLogger(__name__)


def bootstrap(
    m: ConfigModel,
    pipeline: AbstractPipeline | None = None,
    uow: AbstractUnitOfWork | None = None,
) -> MessageBus:
    """Bootstrap the application and return the message bus."""
    seed(m.options.rng_seed)

    quota = DiversityQuota(
        root=m.root,
        max_per_dir=m.options.max_per_dir,
        unique_files_only=m.options.is_create_unique_dirs,
    )
    job = TransferJob(quota=quota)

    if pipeline is None:
        pipeline = TransferPipeline(
            is_create_dir=m.directory.is_enabled,
            fs=ConcreteFilesystemPort(),
            logging=ConcreteLoggingPort(),
            filecount_fn=get_filecount_fn(
                m.filecount.count,
                m.filecount.rand_min,
                m.filecount.rand_max,
                is_rand_enabled=m.filecount.is_rand_enabled,
            ),
            dirname_fn=get_dirname_fn(
                m.dest,
                m.directory.name,
                is_enabled=m.directory.is_enabled,
            ),
            filefilter_fn=get_filefilter_fn(
                m,
            ),
            filenamer_fn=get_filenamer_fn(
                m.filename.template,
                is_enabled=m.filename.is_enabled,
            ),
            transfer_fn=get_transfer_fn(
                m.options.transfer_mode,
            ),
            walker_fn=get_walker_fn(
                m.root,
                should_follow_symlink=m.options.should_follow_symlink,
            ),
        )

    if uow is None and isinstance(pipeline, TransferPipeline):
        uow = FileSystemUnitOfWork(pipeline=pipeline, job=job)

    if uow is None:
        msg = "Unit of Work must be provided if pipeline is not a TransferPipeline."
        raise ValueError(msg)

    return MessageBus(uow=uow, event_handlers=EVENT_HANDLERS, command_handlers=COMMAND_HANDLERS)
