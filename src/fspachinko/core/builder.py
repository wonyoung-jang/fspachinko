"""Builder module for core functionality."""

from random import seed
from typing import TYPE_CHECKING

from .engine import Engine
from .verbs.dirnamer import get_dirname_fn
from .verbs.filecounter import get_filecount_fn
from .verbs.filefilter import get_filefilter_fn
from .verbs.filenamer import get_filenamer_fn
from .verbs.transfer import get_transfer_fn
from .verbs.walker import get_walker_fn

if TYPE_CHECKING:
    from .config import ConfigModel
    from .observer import AbstractObserver


def build_engine(m: ConfigModel, observer: AbstractObserver) -> Engine:
    """Build and return the engine based on the configuration."""
    seed(m.options.rng_seed)

    return Engine(
        root=m.root,
        is_create_folder=m.directory.is_enabled,
        dir_count=m.directory.count,
        max_per_dir=m.options.max_per_dir,
        is_create_unique_dirs=m.options.is_create_unique_dirs,
        filecount_fn=get_filecount_fn(m.filecount),
        dirname_fn=get_dirname_fn(m.directory, m.dest),
        filefilter_fn=get_filefilter_fn(m),
        filenamer_fn=get_filenamer_fn(m.filename),
        transfer_fn=get_transfer_fn(m.options.transfer_mode),
        walker_fn=get_walker_fn(m.root, should_follow_symlink=m.options.should_follow_symlink),
        observer=observer,
    )
