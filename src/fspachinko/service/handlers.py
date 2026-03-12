"""Handlers module."""

import logging
import re
from io import UnsupportedOperation
from os import link, symlink, unlink
from os.path import join
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING

from ..adapters.dirnamer import AbstractDirectoryNamer, StaticDirectoryNamer, UniqueDirectoryNamer
from ..adapters.filecounter import AbstractFileCounter, RandomFileCounter, StaticFileCounter
from ..adapters.filefilter import (
    AbstractFileFilter,
    CompositeFileFilter,
    DirnameFilter,
    DurationFilter,
    ExcludeTextFilter,
    ExcludeTextFilterSingular,
    ExtensionFilter,
    FilesizeFilter,
    Filter,
    IncludeTextFilter,
    IncludeTextFilterSingular,
    KeywordFilter,
    NoOpFileFilter,
    RangeFilterFn,
    RangeMaxFilterFn,
    RangeMinFilterFn,
    RangeMinMaxFilterFn,
    SingularFileFilter,
    TextFilterFn,
)
from ..adapters.filenamer import AbstractFilenamer, StaticFilenamer, TemplateFilenamer
from ..adapters.transfer import (
    AbstractTransfer,
    CopyPreserveTransfer,
    CopyTransfer,
    DryRunTransfer,
    HardlinkTransfer,
    MoveTransfer,
    SymlinkTransfer,
)
from ..adapters.walker import AbstractFSWalker, PachinkoFSWalker
from ..constants import SIZE_MAP, TIME_MAP, FilenameTemplate, ReStrFmt, TransferMode
from ..domain.commands import StartProcess, StartProcessingDirectory, StopProcess
from ..domain.events import (
    DirectoryLogged,
    DirectoryStarted,
    Event,
    FileTransferLogged,
    FileTransferred,
    ProcessStarted,
    ProcessStopped,
)
from ..domain.model import DestinationDirectory
from ..helpers import get_report, get_status

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from ..config import ConfigModel, RangeFilterModel, TextFilterModel
    from ..domain.commands import Command
    from .uow import AbstractUnitOfWork

logger = logging.getLogger(__name__)

type Message = Command | Event

######################
## COMMAND HANDLERS ##
######################


def start_process(cmd: StartProcess, uow: AbstractUnitOfWork) -> Iterator[Message]:
    """Handle the StartProcessCommand."""
    yield ProcessStarted(dir_count=cmd.dir_count)
    for di in range(1, cmd.dir_count + 1):
        target_qty = uow.pipeline.get_file_count()
        yield StartProcessingDirectory(dir_idx=di, target_qty=target_qty)
    yield ProcessStopped()


def stop_process(_: StopProcess, uow: AbstractUnitOfWork) -> None:
    """Handle the StopProcessCommand."""
    uow.job.request_stop()


def process_directory(cmd: StartProcessingDirectory, uow: AbstractUnitOfWork) -> Iterator[Message]:
    """Handle the ProcessDirectoryCommand."""
    with uow:
        job = uow.job
        pipeline = uow.pipeline

        if job.is_stop_requested or job.quota.is_root_locked:
            return

        yield DirectoryStarted(idx=cmd.dir_idx, target=cmd.target_qty)

        dst = DestinationDirectory(path=pipeline.get_currdir_dest(), target_qty=cmd.target_qty)
        job.quota.reset()
        pipeline.add_handler(dst.path)

        for e in pipeline.walk():
            if dst.is_success or job.is_stop_requested or job.quota.is_root_locked:
                break
            if not job.process_file(e) or not pipeline.is_valid(e):
                continue
            new_path = pipeline.get_new_path(dst=dst, e=e)
            if new_path:
                uow.register_transfer(e.path, new_path)
                job.update(dst, e)
                yield FileTransferLogged(count=dst.count, src=e.path, dst=new_path)

        is_empty_creation = dst.is_none_found and pipeline.is_create_dir
        pipeline.remove_dst_dir_if_empty(dst.path, none_found=is_empty_creation)
        pipeline.remove_handler()
        status = get_status(
            is_success=dst.is_success,
            is_none_found_and_create_dir=is_empty_creation,
            is_stop_requested=job.is_stop_requested,
            is_root_locked=job.quota.is_root_locked,
        )
        report = get_report(
            dst.path,
            dst.size,
            dst.start_time,
            dst.count,
            dst.target_qty,
        )
        yield DirectoryLogged(status=status, report=report)

        uow.commit()


COMMAND_HANDLERS: dict[type[Command], Callable] = {
    StartProcess: start_process,
    StopProcess: stop_process,
    StartProcessingDirectory: process_directory,
}

####################
## EVENT HANDLERS ##
####################


def handle_process_started(event: ProcessStarted, _: AbstractUnitOfWork) -> None:
    """Handle the StartProcessEvent."""
    logger.debug("%s", event)


def handle_directory_started(event: DirectoryStarted, _: AbstractUnitOfWork) -> None:
    """Handle the DirectoryStartEvent."""
    logger.debug("%s", event)


def handle_file_transferred(event: FileTransferred, _: AbstractUnitOfWork) -> None:
    """Handle the FileTransferredEvent."""
    logger.debug("%s", event)


def handle_finished(event: ProcessStopped, __: AbstractUnitOfWork) -> None:
    """Handle the FinishedEvent."""
    logger.debug("%s", event)


def handle_file_transfer_logged(event: FileTransferLogged, _: AbstractUnitOfWork) -> None:
    """Handle the FileTransferLogged event."""
    logger.info("%s: %s -> %s", event.count, event.src, event.dst)


def handle_directory_logged(event: DirectoryLogged, _: AbstractUnitOfWork) -> None:
    """Handle the DirectoryLogged event."""
    logger.info("%s\n%s", event.status, event.report)


EVENT_HANDLERS: dict[type[Event], list[Callable]] = {
    ProcessStarted: [handle_process_started],
    DirectoryStarted: [handle_directory_started],
    FileTransferred: [handle_file_transferred],
    ProcessStopped: [handle_finished],
    FileTransferLogged: [handle_file_transfer_logged],
    DirectoryLogged: [handle_directory_logged],
}

####################
## OTHER HANDLERS ##
####################


def get_filecount_fn(count: int, rand_min: int, rand_max: int, *, is_rand_enabled: bool) -> AbstractFileCounter:
    """Return a function that determines the number of files to transfer based on the configuration."""
    match is_rand_enabled:
        case True:
            return RandomFileCounter(rand_min, rand_max)
        case False:
            return StaticFileCounter(count)


def get_dirname_fn(dest: str, name: str, *, is_enabled: bool) -> AbstractDirectoryNamer:
    """Return a function that determines the destination folder name based on the configuration."""
    match is_enabled:
        case True:
            return UniqueDirectoryNamer(dest, name)
        case False:
            return StaticDirectoryNamer(dest)


def get_textfilter_fn(m: TextFilterModel, re_fmt: str) -> TextFilterFn | None:
    """Create an include-exclude filter function from configuration model."""
    if not (m.is_enabled and m.text):
        return None

    split_text = set(m.text.split(","))
    patterns = tuple(re.compile(re_fmt.format(re.escape(t)), re.IGNORECASE) for t in split_text)

    match m.should_include, len(patterns) == 1:
        case (True, True):
            return IncludeTextFilterSingular(pattern=patterns[0])
        case (True, False):
            return IncludeTextFilter(patterns=patterns)
        case (False, True):
            return ExcludeTextFilterSingular(pattern=patterns[0])
        case (False, False):
            return ExcludeTextFilter(patterns=patterns)


def get_rangefilter_fn(m: RangeFilterModel, mapping: dict[str, int | float]) -> RangeFilterFn | None:
    """Create a range filter function from it's configuration model."""
    if not m.is_enabled:
        return None

    minimum = m.minimum * mapping.get(m.unit, 1.0)
    maximum = m.maximum * mapping.get(m.unit, 1.0)

    match minimum >= 0, maximum < float("inf"):
        case (True, True):
            return RangeMinMaxFilterFn(minimum=minimum, maximum=maximum)
        case (True, False):
            return RangeMinFilterFn(minimum=minimum)
        case (False, True):
            return RangeMaxFilterFn(maximum=maximum)


def get_filefilter_fn(m: ConfigModel) -> AbstractFileFilter:
    """Create a FileFilter instance from the configuration model."""
    fmap: dict[type[Filter], TextFilterFn | RangeFilterFn | None] = {
        DirnameFilter: get_textfilter_fn(m.dirname, re_fmt=ReStrFmt.DIRECTORY),
        KeywordFilter: get_textfilter_fn(m.keyword, re_fmt=ReStrFmt.KEYWORD),
        ExtensionFilter: get_textfilter_fn(m.extension, re_fmt=ReStrFmt.EXTENSION),
        FilesizeFilter: get_rangefilter_fn(m.filesize, mapping=SIZE_MAP),
        DurationFilter: get_rangefilter_fn(m.duration, mapping=TIME_MAP),
    }
    filters = tuple(filter_c(call=fn) for filter_c, fn in fmap.items() if fn is not None)

    match len(filters) > 0, len(filters) == 1:
        case True, True:
            return SingularFileFilter(filter=filters[0])
        case True, False:
            return CompositeFileFilter(filters=filters)
        case _:
            return NoOpFileFilter()


def get_filenamer_fn(template: str, *, is_enabled: bool) -> AbstractFilenamer:
    """Return a function that determines the destination file name based on the configuration."""
    match not is_enabled or template == FilenameTemplate.ORIGINAL:
        case True:
            return StaticFilenamer()
        case False:
            return TemplateFilenamer(template)


def get_available_transfer_modes() -> dict[TransferMode, AbstractTransfer]:
    """Return the set of available transfer modes based on the current environment."""
    available = {
        TransferMode.DRY_RUN: DryRunTransfer(),
        TransferMode.COPY: CopyTransfer(),
        TransferMode.COPY_PRESERVE: CopyPreserveTransfer(),
        TransferMode.MOVE: MoveTransfer(),
        TransferMode.SYMLINK: SymlinkTransfer(),
        TransferMode.HARDLINK: HardlinkTransfer(),
    }

    def _verify_link_fn(link_func: Callable[[str, str], None], transfer_mode: TransferMode) -> None:
        """Test link creation."""
        try:
            with TemporaryDirectory() as tmpdir:
                test_src = join(tmpdir, "test_src")
                test_link = join(tmpdir, "test_link")
                open(test_src, "w").close()
                link_func(test_src, test_link)
                unlink(test_link)
                unlink(test_src)
        except OSError, UnsupportedOperation, NotImplementedError:
            available.pop(transfer_mode)

    _verify_link_fn(symlink, TransferMode.SYMLINK)
    _verify_link_fn(link, TransferMode.HARDLINK)
    return available


def get_transfer_fn(mode: str | TransferMode) -> AbstractTransfer:
    """Return the appropriate transfer strategy instance.

    Falls back to DRY_RUN if the requested mode is not available.
    """
    available = get_available_transfer_modes()
    return available.get(TransferMode(mode), available[TransferMode.DRY_RUN])


def get_walker_fn(root: str, *, should_follow_symlink: bool) -> AbstractFSWalker:
    """Return a function that generates candidates for a given directory."""
    return PachinkoFSWalker(
        root=root,
        should_follow_symlink=should_follow_symlink,
    )
