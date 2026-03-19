"""Handlers module."""

from dataclasses import dataclass
from os.path import join
from random import randint
from typing import TYPE_CHECKING

from fspachinko.adapters.media import get_duration
from fspachinko.constants import FilenameTemplate, TransferMode
from fspachinko.helpers import get_text_patterns

from ..adapters.filesystemport import get_available_transfer_modes, get_name_from_template, remove_directory, walk
from ..domain.model import DestinationDirectory, FSEntry
from ..helpers import get_report, get_status

if TYPE_CHECKING:
    from collections.abc import Callable

    from fspachinko.adapters.pipeline import AbstractPipeline
    from fspachinko.domain.commands import (
        CreateDirnameFn,
        CreateFilecountFn,
        CreateFilefilterFn,
        CreateFilenameFn,
        CreateRangeFilterFn,
        CreateTextFilterFn,
        CreateTransferFn,
        CreateWalkerFn,
    )

    from ..domain.commands import ProcessDirectory, StopProcess
    from ..domain.events import DirectoryTransferred, FileTransferred
    from .uow import FileSystemUnitOfWork


######################
## COMMAND HANDLERS ##
######################
@dataclass(slots=True)
class ProcessDirectoryHandler:
    """Handle the StartProcessingDirectory command."""

    uow: FileSystemUnitOfWork

    def __call__(self, cmd: ProcessDirectory) -> None:
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
            job.finalize_directory(is_empty_creation=is_empty_creation)
            self.uow.commit()


@dataclass(slots=True)
class StopProcessHandler:
    """Handle the StopProcess command."""

    uow: FileSystemUnitOfWork

    def __call__(self, _: StopProcess) -> None:
        """Handle the StopProcess command."""
        job = self.uow.job
        job.request_stop()


@dataclass(slots=True)
class CreateTransferFnHandler:
    """Handle the CreateTransferFn command."""

    pipeline: AbstractPipeline

    def __call__(self, cmd: CreateTransferFn) -> None:
        """Handle the CreateTransferFn command."""
        available = get_available_transfer_modes()
        self.pipeline.transfer_fn = available.get(TransferMode(cmd.transfermode), available[TransferMode.DRY_RUN])


@dataclass(slots=True)
class CreateFilenameFnHandler:
    """Handle the CreateFilenameFn command."""

    pipeline: AbstractPipeline

    def __call__(self, cmd: CreateFilenameFn) -> None:
        """Handle the CreateFilenameFn command."""
        if not cmd.is_enabled or cmd.template == FilenameTemplate.ORIGINAL:
            self.pipeline.filenamer_fn = lambda e, _: e.stem
        else:
            self.pipeline.filenamer_fn = lambda e, count: get_name_from_template(e, count, cmd.template)


@dataclass(slots=True)
class CreateFilecountFnHandler:
    """Handle the CreateFilecountFn command."""

    pipeline: AbstractPipeline

    def __call__(self, cmd: CreateFilecountFn) -> None:
        """Handle the CreateFilecountFn command."""
        if cmd.is_rand_enabled:
            self.pipeline.filecount_fn = lambda: randint(*cmd.rand_range)
        else:
            self.pipeline.filecount_fn = lambda: cmd.count


@dataclass(slots=True)
class CreateDirnameFnHandler:
    """Handle the CreateDirnameFn command."""

    pipeline: AbstractPipeline

    def __call__(self, cmd: CreateDirnameFn) -> None:
        """Handle the CreateDirnameFn command."""
        if cmd.is_enabled:
            self.pipeline.dirname_fn = lambda: join(cmd.dest, cmd.name)
        else:
            self.pipeline.dirname_fn = lambda: cmd.dest


@dataclass(slots=True)
class CreateWalkerFnHandler:
    """Handle the CreateWalkerFn command."""

    pipeline: AbstractPipeline

    def __call__(self, cmd: CreateWalkerFn) -> None:
        """Handle the CreateWalkerFn command."""
        self.pipeline.walker_fn = lambda board={}, root=cmd.root, should_follow_symlink=cmd.should_follow_symlink: walk(
            board, root, should_follow_symlink=should_follow_symlink
        )


@dataclass(slots=True)
class CreateTextFilterFnHandler:
    """Handle the CreateTextFilterFn command."""

    pipeline: AbstractPipeline

    def __call__(self, cmd: CreateTextFilterFn) -> None:
        """Handle the CreateTextFilterFn command."""
        if not (cmd.is_enabled and cmd.text):
            return
        patterns = get_text_patterns(cmd.text, cmd.re_fmt)
        if cmd.should_include and len(patterns) == 1:
            self.pipeline.filters[cmd.name] = lambda part: patterns[0].search(part) is not None
        elif cmd.should_include:
            self.pipeline.filters[cmd.name] = lambda part: any(p.search(part) for p in patterns)
        elif len(patterns) == 1:
            self.pipeline.filters[cmd.name] = lambda part: patterns[0].search(part) is None
        else:
            self.pipeline.filters[cmd.name] = lambda part: not any(p.search(part) for p in patterns)


@dataclass(slots=True)
class CreateRangeFilterFnHandler:
    """Handle the CreateRangeFilterFn command."""

    pipeline: AbstractPipeline

    def __call__(self, cmd: CreateRangeFilterFn) -> None:
        """Handle the CreateRangeFilterFn command."""
        if not cmd.is_enabled:
            return
        if cmd.minimum >= 0 and cmd.maximum < float("inf"):
            self.pipeline.filters[cmd.name] = lambda val: cmd.minimum <= val <= cmd.maximum
        elif cmd.minimum >= 0:
            self.pipeline.filters[cmd.name] = lambda val: val >= cmd.minimum
        elif cmd.maximum < float("inf"):
            self.pipeline.filters[cmd.name] = lambda val: val <= cmd.maximum


@dataclass(slots=True)
class CreateFilefilterFnHandler:
    """Handle the CreateFilefilterFn command."""

    pipeline: AbstractPipeline

    def __call__(self, _: CreateFilefilterFn) -> None:
        """Handle the CreateFilefilterFn command."""
        filters: list[Callable[[FSEntry], bool]] = []
        for name, fn in self.pipeline.filters.items():
            if name == "dirname_filter":
                filters.append(lambda e, fn=fn: fn(e.parent))
            elif name == "keyword_filter":
                filters.append(lambda e, fn=fn: fn(e.stem))
            elif name == "extension_filter":
                filters.append(lambda e, fn=fn: fn(e.ext))
            elif name == "filesize_filter":
                filters.append(lambda e, fn=fn: fn(e.size))
            elif name == "duration_filter":
                filters.append(lambda e, fn=fn: fn(get_duration(e.path)))

        if filters and len(filters) == 1:
            self.pipeline.filefilter_fn = filters[0]
        elif filters:
            self.pipeline.filefilter_fn = lambda e: all(f(e) for f in filters)
        else:
            self.pipeline.filefilter_fn = lambda _: True


####################
## EVENT HANDLERS ##
####################
@dataclass(slots=True)
class FileTransferredHandler:
    """Handle the FileTransferred event."""

    call: Callable

    def __call__(self, event: FileTransferred) -> None:
        """Handle the FileTransferred event."""
        self.call("%s: '%s' -> '%s'", event.count, event.src, event.dst)


@dataclass(slots=True)
class DirectoryTransferredHandler:
    """Handle the DirectoryTransferred event."""

    call: Callable

    def __call__(self, event: DirectoryTransferred) -> None:
        """Handle the DirectoryTransferred event."""
        status = get_status(
            is_success=event.is_success,
            is_none_found_and_create_dir=event.is_empty_creation,
            is_stop_requested=event.is_stop_requested,
            is_root_locked=event.is_root_locked,
        )
        report = get_report(event.path, event.size, event.count, event.target_qty)
        self.call("%s\n%s", status, report)
