"""Builder module for core functionality."""

from random import seed
from typing import TYPE_CHECKING

from .context import Context, DateTimeStamp, DiversityQuota
from .dirname import get_dirname_fn
from .engine import Engine, JobRequestFactory
from .filecount import get_filecount_fn
from .filefilter import FileFilter
from .filenamer import get_filenamer_fn
from .transfer import get_transfer_fn
from .walker import PachinkoFSWalker

if TYPE_CHECKING:
    from .config import ConfigModel
    from .observer import Observer


def build_engine(m: ConfigModel, observer: Observer) -> Engine:
    """Build and return the engine based on the configuration."""
    seed(m.options.rng_seed)
    dtstamp = DateTimeStamp()
    context = Context(
        root=m.root,
        is_create_folder=m.folder.is_enabled,
    )

    filecount_fn = get_filecount_fn(m.filecount)
    dirname_fn = get_dirname_fn(m.folder, m.dest)
    job_factory = JobRequestFactory(
        filecount_fn=filecount_fn,
        dirname_fn=dirname_fn,
        dir_count=m.folder.count,
    )

    filterer = FileFilter.from_model(m)
    filenamer = get_filenamer_fn(m.filename)
    transferer = get_transfer_fn(mode=m.options.transfer_mode)

    walker = PachinkoFSWalker(
        root=m.root,
        should_follow_symlink=m.options.should_follow_symlink,
    )
    entries = walker()

    quota = DiversityQuota(
        max_per_dir=m.options.max_per_folder,
        is_create_unique_folders=m.options.is_create_unique_folders,
    )

    return Engine(
        context=context,
        filterer=filterer,
        filenamer=filenamer,
        transfer=transferer,
        job_factory=job_factory,
        entries=entries,
        quota=quota,
        dtstamp=dtstamp,
        observer=observer,
    )
