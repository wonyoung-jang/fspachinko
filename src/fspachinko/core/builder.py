"""Builder module for core functionality."""

import logging
from random import seed
from typing import TYPE_CHECKING

from .context import Context, DateTimeStamp, DiversityQuota
from .dirname import get_dirname_fn
from .engine import Engine, JobRequestFactory
from .filecount import get_filecount_fn
from .filefilter import get_filefilter_fn
from .filenamer import get_filenamer_fn
from .transfer import get_transfer_fn
from .walker import PachinkoFSWalker

if TYPE_CHECKING:
    from .config import ConfigModel
    from .observer import Observer

logger = logging.getLogger(__name__)


def build_engine(m: ConfigModel, observer: Observer) -> Engine:
    """Build and return the engine based on the configuration."""
    seed(m.options.rng_seed)
    dtstamp = DateTimeStamp()
    context = Context(
        root=m.root,
        is_create_folder=m.directory.is_enabled,
    )

    filecount_fn = get_filecount_fn(m.filecount)
    dirname_fn = get_dirname_fn(m.directory, m.dest)
    job_factory = JobRequestFactory(
        filecount_fn=filecount_fn,
        dirname_fn=dirname_fn,
        dir_count=m.directory.count,
    )

    filterer = get_filefilter_fn(m)
    filenamer = get_filenamer_fn(m.filename)
    transferer = get_transfer_fn(m.options.transfer_mode)
    logger.info("FileFilter created: %s", filterer)
    logger.info("Filenamer created: %s", filenamer)
    logger.info("Transfer created: %s", transferer)

    walker = PachinkoFSWalker(
        root=m.root,
        should_follow_symlink=m.options.should_follow_symlink,
    )

    quota = DiversityQuota(
        max_per_dir=m.options.max_per_dir,
        is_create_unique_dirs=m.options.is_create_unique_dirs,
    )

    return Engine(
        context=context,
        job_factory=job_factory,
        filterer=filterer,
        filenamer=filenamer,
        transfer=transferer,
        walker=walker,
        quota=quota,
        dtstamp=dtstamp,
        observer=observer,
    )
