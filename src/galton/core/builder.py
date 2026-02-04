"""Builder module for core functionality."""

from random import Random
from typing import TYPE_CHECKING

from galton.utils.timestamp import DateTimeStamp

from ..config import Filecount, Filename, Folder, ListIncludeExclude, MinMax, SizeLimit
from ..utils import SIZE_MAP, TIME_MAP, ReStrFmt
from .engine import Engine
from .quota import DiversityQuota
from .reporter import ReportWriter
from .state import EngineContext
from .transfer import fetch_transfer_strategy
from .validator import FileValidator
from .walker import RandomFSTreeBuilder, RandomFSWalker

if TYPE_CHECKING:
    from ..config import ConfigModel


def build_file_validator(m: ConfigModel) -> FileValidator:
    """Build and return a FileValidator based on the configuration."""
    keywords = ListIncludeExclude.from_model(m.keyword, re_fmt=ReStrFmt.KEYWORD)
    extensions = ListIncludeExclude.from_model(m.extension, re_fmt=ReStrFmt.EXTENSION)
    filesize = MinMax.from_model(m.filesize, mapping=SIZE_MAP)
    duration = MinMax.from_model(m.duration, mapping=TIME_MAP)
    return FileValidator(
        keywords=keywords,
        extensions=extensions,
        filesize=filesize,
        duration=duration,
    )


def build_engine(m: ConfigModel) -> Engine:
    """Build and return the engine based on the configuration."""
    # Build main components
    rng = Random()
    dtstamp = DateTimeStamp()

    # Build FileValidator
    validator = build_file_validator(m)

    # Build DiversityQuota
    quota = DiversityQuota(
        root=m.root,
        is_unique=m.folder.is_unique,
        max_per_dir=m.options.max_per_folder,
    )

    # Build EngineContext
    folder = Folder.from_model(m.folder, dest=m.dest)
    folder_size_limit = SizeLimit.from_model(m.folder_size_limit, mapping=SIZE_MAP)
    total_size_limit = SizeLimit.from_model(m.total_size_limit, mapping=SIZE_MAP)
    reporter = ReportWriter(
        root=m.root,
        exts_str=validator.extensions.as_string,
        keys_str=validator.keywords.as_string,
        dtstamp=dtstamp,
    )
    context = EngineContext(
        folder=folder,
        quota=quota,
        folder_size_limit=folder_size_limit,
        total_size_limit=total_size_limit,
        reporter=reporter,
        is_dry_run=m.options.is_dry_run,
        dtstamp=dtstamp,
    )

    # Build Walker
    tree_builder = RandomFSTreeBuilder(
        root=m.root,
        validator=validator,
        rng=rng,
        should_follow_symlink=m.options.should_follow_symlink,
    )
    tree = tree_builder.build()
    walker = RandomFSWalker(tree=tree, quota=quota)

    # Build Engine
    filecount = Filecount.from_model(m.filecount, rng=rng)
    filename = Filename.from_model(m.filename, dtstamp=dtstamp)
    do_transfer_strategy = fetch_transfer_strategy(m.transfermode.transfer_mode)
    return Engine(
        root=m.root,
        walker=walker,
        validator=validator,
        filecount=filecount,
        filename=filename,
        do_transfer_strategy=do_transfer_strategy,
        context=context,
        folder_count=m.folder.count,
    )
