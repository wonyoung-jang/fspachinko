"""Builder module for core functionality."""

import logging
from random import seed
from typing import TYPE_CHECKING

from .adapters.media import get_duration
from .adapters.pipeline import AbstractPipeline, TransferPipeline
from .constants import SIZE_MAP, TIME_MAP, ReStrFmt
from .domain.model import DiversityQuota, FSEntry, TransferJob
from .service.handlers import (
    COMMAND_HANDLERS,
    EVENT_HANDLERS,
    get_dirname_fn,
    get_filecount_fn,
    get_filefilter_fn,
    get_filenamer_fn,
    get_rangefilter_fn,
    get_textfilter_fn,
    get_transfer_fn,
    get_walker_fn,
)
from .service.messagebus import MessageBus
from .service.uow import AbstractUnitOfWork, FileSystemUnitOfWork

if TYPE_CHECKING:
    from collections.abc import Callable

    from .config import ConfigModel


logger = logging.getLogger(__name__)


def bootstrap(
    m: ConfigModel,
    pipeline: AbstractPipeline | None = None,
    uow: AbstractUnitOfWork | None = None,
) -> MessageBus:
    """Bootstrap the application and return the message bus."""
    seed(m.options.rng_seed)

    quota = DiversityQuota(
        root=m.root,
        max_per_dir=m.options.max_per_dir,
        unique_files_only=m.options.is_create_unique_dirs,
    )
    job = TransferJob(quota=quota)

    if pipeline is None:
        pipeline = build_pipeline(m)

    if uow is None and isinstance(pipeline, TransferPipeline):
        uow = FileSystemUnitOfWork(pipeline=pipeline, job=job)

    if uow is None:
        msg = "Unit of Work must be provided if pipeline is not a TransferPipeline."
        raise ValueError(msg)

    return MessageBus(uow=uow, event_handlers=EVENT_HANDLERS, command_handlers=COMMAND_HANDLERS)


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

    filter_list: list[Callable[[FSEntry], bool]] = []
    if dirname_filter_fn:
        filter_list.append(lambda e: dirname_filter_fn(e.parent))
    if keyword_filter_fn:
        filter_list.append(lambda e: keyword_filter_fn(e.stem))
    if extension_filter_fn:
        filter_list.append(lambda e: extension_filter_fn(e.ext))
    if filesize_filter_fn:
        filter_list.append(lambda e: filesize_filter_fn(e.size))
    if duration_filter_fn:
        filter_list.append(lambda e: duration_filter_fn(get_duration(e.path)))
    return tuple(filter_list)


def build_pipeline(m: ConfigModel) -> AbstractPipeline:
    """Build the pipeline based on the configuration."""
    filters = build_filters(m)
    return TransferPipeline(
        is_create_dir=m.directory.is_enabled,
        filecount_fn=get_filecount_fn(
            m.filecount.count,
            m.filecount.rand_min,
            m.filecount.rand_max,
            is_rand_enabled=m.filecount.is_rand_enabled,
        ),
        dirname_fn=get_dirname_fn(
            m.dest,
            m.directory.name,
            is_enabled=m.directory.is_enabled,
        ),
        filefilter_fn=get_filefilter_fn(filters),
        filenamer_fn=get_filenamer_fn(
            m.filename.template,
            is_enabled=m.filename.is_enabled,
        ),
        transfer_fn=get_transfer_fn(
            m.options.transfer_mode,
        ),
        walker_fn=get_walker_fn(
            m.root,
            should_follow_symlink=m.options.should_follow_symlink,
        ),
    )
