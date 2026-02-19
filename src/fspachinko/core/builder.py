"""Builder module for core functionality."""

from random import seed
from typing import TYPE_CHECKING

from .config import Filenamer, get_dirname_fn, get_filecount_fn
from .context import DateTimeStamp, DiversityQuota, EngineContext
from .engine import Engine, JobRequestFactory
from .filefilter import FileFilter
from .transfer import get_transfer_strategy
from .walker import PachinkoFSWalker

if TYPE_CHECKING:
    from .config import ConfigModel
    from .observer import Observer


def build_engine(m: ConfigModel, observer: Observer) -> Engine:
    """Build and return the engine based on the configuration."""
    seed(m.options.rng_seed)
    dtstamp = DateTimeStamp()
    context = EngineContext(
        root=m.root,
        is_create_folder=m.folder.is_enabled,
        is_dry_run=m.options.is_dry_run,
    )
    filterer = FileFilter.from_model(m)
    filenamer = Filenamer.from_model(m.filename)
    transferer = get_transfer_strategy(m.options.transfer_mode)
    job_request_factory = JobRequestFactory(
        filecount_fn=get_filecount_fn(m.filecount),
        dirname_fn=get_dirname_fn(m.folder, m.dest),
        dir_count=m.folder.count,
    )
    walker = PachinkoFSWalker(
        root=m.root,
        should_follow_symlink=m.options.should_follow_symlink,
    ).walk()
    quota = DiversityQuota(
        max_per_dir=m.options.max_per_folder,
        is_create_unique_folders=m.options.is_create_unique_folders,
    )
    return Engine(
        context=context,
        filterer=filterer,
        filenamer=filenamer,
        transferer=transferer,
        job_factory=job_request_factory,
        entries=walker,
        quota=quota,
        dtstamp=dtstamp,
        observer=observer,
    )
