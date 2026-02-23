"""Builder module for core functionality."""

from random import randint, seed
from typing import TYPE_CHECKING

from .context import Context, DateTimeStamp, DiversityQuota
from .engine import Engine, JobRequestFactory
from .filefilter import FileFilter
from .filenamer import Filenamer
from .helpers import calc_unique_path_name
from .transfer import get_transfer_fn
from .walker import PachinkoFSWalker

if TYPE_CHECKING:
    from collections.abc import Callable

    from .config import ConfigModel, DirectoryModel, FilecountModel
    from .observer import Observer


def get_filecount_fn(m: FilecountModel) -> Callable[[], int]:
    """Return a function that determines the number of files to transfer based on the configuration."""
    return (
        (lambda rmin=m.rand_min, rmax=m.rand_max: randint(rmin, rmax))
        if m.is_rand_enabled
        else (lambda count=m.count: count)
    )


def get_dirname_fn(m: DirectoryModel, dest: str) -> Callable[[], str]:
    """Return a function that determines the destination folder name based on the configuration."""
    return (lambda name=m.name: calc_unique_path_name(dest, name)) if m.is_enabled else (lambda: dest)


def build_engine(m: ConfigModel, observer: Observer) -> Engine:
    """Build and return the engine based on the configuration."""
    seed(m.options.rng_seed)
    dtstamp = DateTimeStamp()
    context = Context(
        root=m.root,
        is_create_folder=m.folder.is_enabled,
    )
    filterer = FileFilter.from_model(m)
    filenamer = Filenamer.from_model(m.filename)
    transferer = get_transfer_fn(mode=m.options.transfer_mode)
    job_factory = JobRequestFactory(
        filecount_fn=get_filecount_fn(m.filecount),
        dirname_fn=get_dirname_fn(m.folder, m.dest),
        dir_count=m.folder.count,
    )
    walker = PachinkoFSWalker(
        root=m.root,
        should_follow_symlink=m.options.should_follow_symlink,
    )
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
        entries=walker(),
        quota=quota,
        dtstamp=dtstamp,
        observer=observer,
    )
