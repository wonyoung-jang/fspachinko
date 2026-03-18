"""Builder module for core functionality."""

import logging
import re
from os.path import join
from random import randint, seed
from typing import TYPE_CHECKING

from .adapters.filesystemport import get_available_transfer_modes, get_name_from_template, walk
from .adapters.media import get_duration
from .adapters.pipeline import AbstractPipeline, TransferPipeline
from .constants import SIZE_MAP, TIME_MAP, FilenameTemplate, ReStrFmt, TransferMode
from .domain.commands import ProcessDirectory, StopProcess
from .domain.events import DirectoryTransferred, FileTransferred
from .domain.model import DiversityQuota, FSEntry, TransferJob
from .service.handlers import (
    DirectoryTransferredHandler,
    FileTransferredHandler,
    ProcessDirectoryHandler,
    StopProcessHandler,
)
from .service.messagebus import MessageBus
from .service.uow import AbstractUnitOfWork, FileSystemUnitOfWork

if TYPE_CHECKING:
    from collections.abc import Callable

    from .configuration.model import ConfigModel

logger = logging.getLogger(__name__)


def bootstrap(
    m: ConfigModel,
    pipeline: AbstractPipeline | None = None,
    uow: AbstractUnitOfWork | None = None,
) -> MessageBus:
    """Bootstrap the application and return the message bus."""
    seed(m.options.rng_seed)
    job = TransferJob(
        quota=DiversityQuota(
            root=m.root,
            max_per_dir=m.options.max_per_dir,
            unique_files_only=m.options.is_create_unique_dirs,
        )
    )
    if pipeline is None:
        pipeline = build_pipeline(m)
    if uow is None and isinstance(pipeline, TransferPipeline):
        uow = FileSystemUnitOfWork(pipeline=pipeline, job=job)
    if uow is None:
        msg = "Unit of Work must be provided if pipeline is not a TransferPipeline."
        raise ValueError(msg)
    event_handlers = {
        FileTransferred: [FileTransferredHandler(call=logger.info)],
        DirectoryTransferred: [DirectoryTransferredHandler(call=logger.info)],
    }
    command_handlers = {
        ProcessDirectory: ProcessDirectoryHandler(uow=uow),
        StopProcess: StopProcessHandler(uow=uow),
    }
    return MessageBus(
        uow=uow,
        event_handlers=event_handlers,
        command_handlers=command_handlers,
    )


def build_filters(m: ConfigModel) -> tuple[Callable[[FSEntry], bool], ...]:
    """Build the filters based on the configuration."""
    dirname_filter_fn = get_textfilter_fn(
        text=m.dirname.text,
        re_fmt=ReStrFmt.DIRECTORY,
        is_enabled=m.dirname.is_enabled,
        should_include=m.dirname.should_include,
    )
    keyword_filter_fn = get_textfilter_fn(
        text=m.keyword.text,
        re_fmt=ReStrFmt.KEYWORD,
        is_enabled=m.keyword.is_enabled,
        should_include=m.keyword.should_include,
    )
    extension_filter_fn = get_textfilter_fn(
        text=m.extension.text,
        re_fmt=ReStrFmt.EXTENSION,
        is_enabled=m.extension.is_enabled,
        should_include=m.extension.should_include,
    )
    filesize_filter_fn = get_rangefilter_fn(
        minimum=m.filesize.minimum,
        maximum=m.filesize.maximum,
        unit=m.filesize.unit,
        mapping=SIZE_MAP,
        is_enabled=m.filesize.is_enabled,
    )
    duration_filter_fn = get_rangefilter_fn(
        minimum=m.duration.minimum,
        maximum=m.duration.maximum,
        unit=m.duration.unit,
        mapping=TIME_MAP,
        is_enabled=m.duration.is_enabled,
    )
    filters: list[Callable[[FSEntry], bool]] = []
    if dirname_filter_fn:
        filters.append(lambda e: dirname_filter_fn(e.parent))
    if keyword_filter_fn:
        filters.append(lambda e: keyword_filter_fn(e.stem))
    if extension_filter_fn:
        filters.append(lambda e: extension_filter_fn(e.ext))
    if filesize_filter_fn:
        filters.append(lambda e: filesize_filter_fn(e.size))
    if duration_filter_fn:
        filters.append(lambda e: duration_filter_fn(get_duration(e.path)))
    return tuple(filters)


def build_pipeline(m: ConfigModel) -> AbstractPipeline:
    """Build the pipeline based on the configuration."""
    pipeline = TransferPipeline()
    pipeline.is_create_dir = m.directory.is_enabled
    pipeline.filefilter_fn = get_filefilter_fn(build_filters(m))
    pipeline.filenamer_fn = get_filenamer_fn(
        m.filename.template,
        is_enabled=m.filename.is_enabled,
    )
    pipeline.transfer_fn = get_transfer_fn(m.options.transfer_mode)
    pipeline.walker_fn = get_walker_fn(
        board={},
        root=m.root,
        should_follow_symlink=m.options.should_follow_symlink,
    )
    pipeline.filecount_fn = get_filecount_fn(
        m.filecount.count,
        m.filecount.rand_min,
        m.filecount.rand_max,
        is_rand_enabled=m.filecount.is_rand_enabled,
    )
    pipeline.dirname_fn = get_dirname_fn(
        m.dest,
        m.directory.name,
        is_enabled=m.directory.is_enabled,
    )
    return pipeline


#####################
## FACTORY METHODS ##
#####################


def get_filecount_fn(count: int, rand_min: int, rand_max: int, *, is_rand_enabled: bool) -> Callable:
    """Return a function that determines the number of files to transfer based on the configuration."""
    if is_rand_enabled:
        return lambda: randint(rand_min, rand_max)
    return lambda: count


def get_dirname_fn(dest: str, name: str, *, is_enabled: bool) -> Callable:
    """Return a function that determines the destination folder name based on the configuration."""
    if is_enabled:
        return lambda: join(dest, name)
    return lambda: dest


def get_textfilter_fn(text: str, re_fmt: str, *, is_enabled: bool, should_include: bool) -> Callable | None:
    """Create an include-exclude filter function from configuration model."""
    if not (is_enabled and text):
        return None
    split_text = set(text.split(","))
    patterns = tuple(re.compile(re_fmt.format(re.escape(t)), re.IGNORECASE) for t in split_text)
    match should_include, len(patterns) == 1:
        case (True, True):
            return lambda part: patterns[0].search(part) is not None
        case (True, False):
            return lambda part: any(p.search(part) for p in patterns)
        case (False, True):
            return lambda part: patterns[0].search(part) is None
        case (False, False):
            return lambda part: not any(p.search(part) for p in patterns)


def get_rangefilter_fn(
    minimum: float, maximum: float, unit: str, mapping: dict[str, int | float], *, is_enabled: bool
) -> Callable | None:
    """Create a range filter function from it's configuration model."""
    if not is_enabled:
        return None
    min_val = minimum * mapping.get(unit, 1.0)
    max_val = maximum * mapping.get(unit, 1.0)
    match min_val >= 0, max_val < float("inf"):
        case (True, True):
            return lambda val: min_val <= val <= max_val
        case (True, False):
            return lambda val: val >= min_val
        case (False, True):
            return lambda val: val <= max_val
    return None


def get_filefilter_fn(filters: tuple[Callable, ...]) -> Callable:
    """Create a FileFilter instance from the configuration model."""
    match len(filters) > 0, len(filters) == 1:
        case True, True:
            return filters[0]
        case True, False:
            return lambda e: all(f(e) for f in filters)
        case _:
            return lambda _: True


def get_filenamer_fn(template: str, *, is_enabled: bool) -> Callable[[FSEntry, int], str]:
    """Return a function that determines the destination file name based on the configuration."""
    if not is_enabled or template == FilenameTemplate.ORIGINAL:
        return lambda e, _: e.stem
    return lambda e, count: get_name_from_template(e, count, template)


def get_transfer_fn(mode: str) -> Callable:
    """Return the appropriate transfer strategy instance.

    Falls back to DRY_RUN if the requested mode is not available.
    """
    available = get_available_transfer_modes()
    return available.get(TransferMode(mode), available[TransferMode.DRY_RUN])


def get_walker_fn(board: dict, root: str, *, should_follow_symlink: bool) -> Callable:
    """Return a function that generates candidates for a given directory."""
    return lambda board=board, root=root, should_follow_symlink=should_follow_symlink: walk(
        board, root, should_follow_symlink=should_follow_symlink
    )
