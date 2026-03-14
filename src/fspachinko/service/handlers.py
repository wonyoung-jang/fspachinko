"""Handlers module."""

import logging
import re
from dataclasses import dataclass
from os.path import join
from random import randint
from typing import TYPE_CHECKING

from ..adapters.filenamer import get_name_from_template
from ..adapters.filesystemport import get_available_transfer_modes, remove_directory, walk
from ..constants import FilenameTemplate, TransferMode
from ..domain.events import DirectoryTransferred, Event, FileTransferred
from ..domain.model import DestinationDirectory, FSEntry
from ..helpers import get_report, get_status

if TYPE_CHECKING:
    from collections.abc import Callable

    from ..domain.commands import Command, StartProcessingDirectory, StopProcess
    from .uow import AbstractUnitOfWork

logger = logging.getLogger(__name__)

type Message = Command | Event

######################
## COMMAND HANDLERS ##
######################


@dataclass(slots=True)
class StartProcessingDirectoryHandler:
    """Handle the StartProcessingDirectory command."""

    uow: AbstractUnitOfWork

    def __call__(self, cmd: StartProcessingDirectory) -> None:
        """Handle the StartProcessingDirectory command."""
        with self.uow:
            job = self.uow.job
            if job.is_stop_requested or job.is_root_locked:
                return

            job.reset()
            job.dst = DestinationDirectory(cmd.path, cmd.target_qty)

            for entry in self.uow.pipeline.walker_fn():
                if job.dst.is_success or job.is_stop_requested or job.is_root_locked:
                    break

                if not job.process_file(entry) or not self.uow.pipeline.filefilter_fn(entry):
                    continue

                new_path = self.uow.pipeline.get_new_path(dst=job.dst, e=entry)
                if new_path:
                    self.uow.register_transfer(entry.path, new_path)
                    job.update(entry, new_path)

            is_empty_creation = job.dst.is_none_found and self.uow.pipeline.is_create_dir
            if is_empty_creation:
                remove_directory(job.dst.path)

            job.finalize_directory(
                status=get_status(
                    is_success=job.dst.is_success,
                    is_none_found_and_create_dir=is_empty_creation,
                    is_stop_requested=job.is_stop_requested,
                    is_root_locked=job.is_root_locked,
                ),
                report=get_report(job.dst.path, job.dst.size, job.dst.count, job.dst.target_qty),
            )

            self.uow.commit()


@dataclass(slots=True)
class StopProcessHandler:
    """Handle the StopProcess command."""

    uow: AbstractUnitOfWork

    def __call__(self, _: StopProcess) -> None:
        """Handle the StopProcess command."""
        job = self.uow.job
        job.request_stop()


####################
## EVENT HANDLERS ##
####################


class FileTransferredHandler:
    """Handle the FileTransferred event."""

    def __call__(self, event: FileTransferred) -> None:
        """Handle the FileTransferred event."""
        logger.info("%s: %s -> %s", event.count, event.src, event.dst)


class DirectoryTransferredHandler:
    """Handle the DirectoryTransferred event."""

    def __call__(self, event: DirectoryTransferred) -> None:
        """Handle the DirectoryTransferred event."""
        logger.info("%s\n%s", event.status, event.report)


####################
## OTHER HANDLERS ##
####################


def get_filecount_fn(count: int, rand_min: int, rand_max: int, *, is_rand_enabled: bool) -> Callable:
    """Return a function that determines the number of files to transfer based on the configuration."""
    match is_rand_enabled:
        case True:
            return lambda: randint(rand_min, rand_max)
        case False:
            return lambda: count


def get_dirname_fn(dest: str, name: str, *, is_enabled: bool) -> Callable:
    """Return a function that determines the destination folder name based on the configuration."""
    match is_enabled:
        case True:
            return lambda: join(dest, name)
        case False:
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
        case _:
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


def get_filenamer_fn(
    template: str, *, is_enabled: bool
) -> Callable[[FSEntry, int, str], str] | Callable[[FSEntry, int], str]:
    """Return a function that determines the destination file name based on the configuration."""
    match not is_enabled or template == FilenameTemplate.ORIGINAL:
        case True:
            return lambda e, _: e.stem
        case False:
            return lambda e, count, template=template: get_name_from_template(e, count, template)


def get_transfer_fn(mode: str | TransferMode) -> Callable:
    """Return the appropriate transfer strategy instance.

    Falls back to DRY_RUN if the requested mode is not available.
    """
    available = get_available_transfer_modes()
    return available.get(TransferMode(mode), available[TransferMode.DRY_RUN])


def get_walker_fn(root: str, *, should_follow_symlink: bool) -> Callable:
    """Return a function that generates candidates for a given directory."""
    return lambda board={}, root=root, should_follow_symlink=should_follow_symlink: walk(
        board, root, should_follow_symlink=should_follow_symlink
    )
