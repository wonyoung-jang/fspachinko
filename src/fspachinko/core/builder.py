"""Builder module for core functionality."""

from random import seed
from typing import TYPE_CHECKING

from fspachinko.core.destination import JobRequestFactory

from ..config import Filecount, Filename, Folder, ListIncludeExclude, MinMax, SizeLimit
from ..utils import SIZE_MAP, TIME_MAP, DateTimeStamp, ReStrFmt
from .engine import Engine
from .quota import DiversityQuota
from .reporter import ReportWriter
from .state import EngineContext
from .transfer import fetch_transfer_strategy
from .validator import FileValidator
from .walker import PachinkoFSWalker

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
    seed(m.options.rng_seed)
    dtstamp = DateTimeStamp()

    # Build FileValidator
    validator = build_file_validator(m)

    # Build DiversityQuota
    quota = DiversityQuota(
        root=m.root,
        max_per_dir=m.options.max_per_folder,
        is_create_unique_folders=m.options.is_create_unique_folders,
    )

    # Build EngineContext
    folder = Folder.from_model(m.folder, dest=m.dest)
    folder_size_limit = SizeLimit.from_model(m.folder_size_limit, mapping=SIZE_MAP)
    total_size_limit = SizeLimit.from_model(m.total_size_limit, mapping=SIZE_MAP)
    reporter = ReportWriter(root=m.root, dtstamp=dtstamp)
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
    walker = PachinkoFSWalker(
        root=m.root,
        quota=quota,
        validator=validator,
        should_follow_symlink=m.options.should_follow_symlink,
    )

    # Build Engine
    filecount = Filecount.from_model(m.filecount)
    filename = Filename.from_model(m.filename, dtstamp=dtstamp)
    do_transfer_strategy = fetch_transfer_strategy(m.transfermode.transfer_mode)

    job_request_factory = JobRequestFactory(
        get_file_count=filecount.get_file_count,
        determine_dest_dirname=folder.determine_dest_dirname,
        dir_count=m.folder.count,
    )
    return Engine(
        root=m.root,
        walker=walker,
        validator=validator,
        filename=filename,
        do_transfer_strategy=do_transfer_strategy,
        context=context,
        job_request_factory=job_request_factory,
    )
