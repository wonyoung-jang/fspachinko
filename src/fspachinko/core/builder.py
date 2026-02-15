"""Builder module for core functionality."""

from random import seed
from typing import TYPE_CHECKING

from .config import Filename, ListIncludeExclude, MinMax
from .constants import SIZE_MAP, TIME_MAP, ReStrFmt
from .context import DateTimeStamp, DiversityQuota, EngineContext
from .engine import Engine, JobRequestFactory
from .transfer import fetch_transfer_strategy
from .validator import FileValidator, FileValidatorBuilder
from .walker import PachinkoFSWalker

if TYPE_CHECKING:
    from .config import ConfigModel
    from .observer import Observer


def build_file_validator(m: ConfigModel) -> FileValidator:
    """Build and return a FileValidator based on the configuration."""
    directory_name = ListIncludeExclude.from_model(m.directory_name, re_fmt=ReStrFmt.DIRECTORY)
    keywords = ListIncludeExclude.from_model(m.keyword, re_fmt=ReStrFmt.KEYWORD)
    extensions = ListIncludeExclude.from_model(m.extension, re_fmt=ReStrFmt.EXTENSION)
    filesize = MinMax.from_model(m.filesize, mapping=SIZE_MAP)
    duration = MinMax.from_model(m.duration, mapping=TIME_MAP)
    validators = FileValidatorBuilder(
        directory_name=directory_name,
        keywords=keywords,
        extensions=extensions,
        filesize=filesize,
        duration=duration,
    ).build()
    return FileValidator(validators=validators)


def build_engine(m: ConfigModel, observer: Observer) -> Engine:
    """Build and return the engine based on the configuration."""
    # Build main components
    seed(m.options.rng_seed)
    dtstamp = DateTimeStamp()

    # Build FileValidator
    validator = build_file_validator(m)

    # Build DiversityQuota
    quota = DiversityQuota(
        max_per_dir=m.options.max_per_folder,
        is_create_unique_folders=m.options.is_create_unique_folders,
    )

    # Build EngineContext
    context = EngineContext(
        root=m.root,
        is_create_folder=m.folder.is_enabled,
        is_dry_run=m.options.is_dry_run,
        quota=quota,
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
    filename = Filename(m.filename.template, dtstamp=dtstamp)

    job_request_factory = JobRequestFactory(
        get_file_count=m.filecount.get_count_fn(),
        determine_dest_dirname=m.folder.get_dirname_fn(m.dest),
        dir_count=m.folder.count,
    )
    return Engine(
        root=m.root,
        context=context,
        filename_fn=filename.determine_dest_filename,
        transfer_fn=fetch_transfer_strategy(m.options.transfer_mode),
        job_request_factory=job_request_factory,
        entries=walker.walk(),
        observer=observer,
    )
