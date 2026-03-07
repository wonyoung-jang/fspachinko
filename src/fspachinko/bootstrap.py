"""Builder module for core functionality."""

import logging
from random import seed
from typing import TYPE_CHECKING

from .adapters import ConcreteLoggingPort
from .adapters.dirnamer import get_dirname_fn
from .adapters.filecounter import get_filecount_fn
from .adapters.filefilter import get_filefilter_fn
from .adapters.filenamer import get_filenamer_fn
from .adapters.filesystemport import ConcreteFilesystemPort
from .adapters.pipeline import TransferPipeline
from .adapters.transfer import get_transfer_fn
from .adapters.walker import get_walker_fn
from .domain.model import DiversityQuota
from .service.handlers import COMMAND_HANDLERS, EVENT_HANDLERS, Engine
from .service.messagebus import MessageBus
from .service.uow import AbstractUnitOfWork, InMemoryUnitOfWork

if TYPE_CHECKING:
    from .config import ConfigModel


logger = logging.getLogger(__name__)


def bootstrap(
    m: ConfigModel,
    uow: AbstractUnitOfWork | None = None,
) -> MessageBus:
    """Bootstrap the application and return the message bus."""
    seed(m.options.rng_seed)

    quota = DiversityQuota(
        root=m.root,
        max_per_dir=m.options.max_per_dir,
        unique_files_only=m.options.is_create_unique_dirs,
    )
    is_create_dir = m.directory.is_enabled

    pipeline = TransferPipeline(
        is_create_dir=is_create_dir,
        fs=ConcreteFilesystemPort(),
        filecount_fn=get_filecount_fn(m.filecount),
        dirname_fn=get_dirname_fn(m.directory, m.dest),
        filefilter_fn=get_filefilter_fn(m),
        filenamer_fn=get_filenamer_fn(m.filename),
        transfer_fn=get_transfer_fn(m.options.transfer_mode),
        walker_fn=get_walker_fn(m.root, should_follow_symlink=m.options.should_follow_symlink),
    )
    engine = Engine(
        dir_count=m.directory.count if is_create_dir else 1,
        is_create_dir=is_create_dir,
        pipeline=pipeline,
        quota=quota,
        logging=ConcreteLoggingPort(),
    )

    if uow is None:
        uow = InMemoryUnitOfWork(
            engine=engine,
        )

    return MessageBus(
        uow=uow,
        event_handlers=EVENT_HANDLERS,
        command_handlers=COMMAND_HANDLERS,
    )
