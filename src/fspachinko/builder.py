"""Builder module for core functionality."""

import logging
from random import seed
from typing import TYPE_CHECKING

from .adapters import ConcreteLoggingPort
from .adapters.filesystemport import ConcreteFilesystemPort
from .adapters.transfer import get_transfer_fn
from .adapters.walker import get_walker_fn
from .core.verbs.dirnamer import get_dirname_fn
from .core.verbs.filecounter import get_filecount_fn
from .core.verbs.filefilter import get_filefilter_fn
from .core.verbs.filenamer import get_filenamer_fn
from .domain.model import DiversityQuota, Engine
from .service.handlers import COMMAND_HANDLERS, EVENT_HANDLERS
from .service.messagebus import MessageBus
from .service.uow import InMemoryUnitOfWork

if TYPE_CHECKING:
    from .core.config import ConfigModel


logger = logging.getLogger(__name__)


def bootstrap(m: ConfigModel) -> MessageBus:
    """Bootstrap the application and return the message bus."""
    seed(m.options.rng_seed)

    engine = build_engine(m)
    uow = InMemoryUnitOfWork(engine=engine)

    return MessageBus(
        uow=uow,
        event_handlers=EVENT_HANDLERS,
        command_handlers=COMMAND_HANDLERS,
    )


def build_engine(m: ConfigModel) -> Engine:
    """Build and return the engine based on the configuration."""
    quota = DiversityQuota(
        max_per_dir=m.options.max_per_dir,
        unique_files_only=m.options.is_create_unique_dirs,
    )
    return Engine(
        root=m.root,
        dir_count=m.directory.count,
        is_create_dir=m.directory.is_enabled,
        filecount_fn=get_filecount_fn(m.filecount),
        dirname_fn=get_dirname_fn(m.directory, m.dest),
        filefilter_fn=get_filefilter_fn(m),
        filenamer_fn=get_filenamer_fn(m.filename),
        transfer_fn=get_transfer_fn(m.options.transfer_mode),
        walker_fn=get_walker_fn(m.root, should_follow_symlink=m.options.should_follow_symlink),
        quota=quota,
        filesystem=ConcreteFilesystemPort(),
        logging=ConcreteLoggingPort(logger),
    )
