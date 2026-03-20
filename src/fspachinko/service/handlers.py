"""Handlers module."""

from dataclasses import dataclass
from os.path import join
from random import randint
from typing import TYPE_CHECKING

from fspachinko.adapters.filesystemport import (
    get_available_transfer_modes,
    get_name_from_template,
    remove_directory,
)
from fspachinko.adapters.fswalker import FSWalker
from fspachinko.adapters.media import get_duration
from fspachinko.constants import FilenameTemplate, FilterName, TransferMode
from fspachinko.domain.model import DestinationDirectory, DiversityQuota, FSEntry, TransferJob
from fspachinko.helpers import get_report, get_status, get_text_patterns

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from fspachinko.adapters.pipeline import AbstractPipeline
    from fspachinko.domain.commands import (
        CreateDirnameFn,
        CreateFilecountFn,
        CreateFilefilterFn,
        CreateFilenameFn,
        CreateRangeFilterFn,
        CreateTextFilterFn,
        CreateTransferFn,
        CreateTransferJob,
        CreateWalkerFn,
        ProcessDirectory,
        SetPipelineCreateDir,
        SetRngSeed,
        StopProcess,
    )
    from fspachinko.domain.events import DirectoryTransferred, FileTransferred

    from .uow import FileSystemUnitOfWork


######################
## COMMAND HANDLERS ##
######################
@dataclass(slots=True)
class CreateTransferJobHandler:
    """Handle the CreateTransferJob command."""

    uow: FileSystemUnitOfWork

    def __call__(self, cmd: CreateTransferJob) -> None:
        """Handle the CreateTransferJob command."""
        self.uow.job = TransferJob(
            quota=DiversityQuota(
                root=cmd.root,
                max_per_dir=cmd.max_per_dir,
                unique_files_only=cmd.unique_files_only,
            ),
        )


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
class SetRngSeedHandler:
    """Handle the SetRngSeed command."""

    rng_seed_fn: Callable

    def __call__(self, cmd: SetRngSeed) -> None:
        """Handle the SetRngSeed command."""
        self.rng_seed_fn(cmd.rng_seed)


@dataclass(slots=True)
class SetPipelineCreateDirHandler:
    """Handle the SetPipelineCreateDir command."""

    pipeline: AbstractPipeline

    def __call__(self, cmd: SetPipelineCreateDir) -> None:
        """Handle the SetPipelineCreateDir command."""
        self.pipeline.is_create_dir = cmd.is_create_dir


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
            self.pipeline.filenamer_fn = lambda e, count, t=cmd.template: get_name_from_template(e, count, t)


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
        self.pipeline.walker_fn = FSWalker(root=cmd.root, should_follow_symlink=cmd.should_follow_symlink)


@dataclass(slots=True)
class CreateTextFilterFnHandler:
    """Handle the CreateTextFilterFn command."""

    pipeline: AbstractPipeline

    def __call__(self, cmd: CreateTextFilterFn) -> None:
        """Handle the CreateTextFilterFn command."""
        if not (cmd.is_enabled and cmd.text):
            return

        should_include = cmd.should_include
        patterns = get_text_patterns(cmd.text, cmd.re_fmt)

        def _get_text_filter() -> Callable[[str], bool]:
            if should_include and len(patterns) == 1:
                return lambda p: patterns[0].search(p) is not None
            if should_include:
                return lambda p: any(pattern.search(p) for pattern in patterns)
            if len(patterns) == 1:
                return lambda p: patterns[0].search(p) is None
            return lambda p: not any(pattern.search(p) for pattern in patterns)

        self.pipeline.filters[cmd.name] = _get_text_filter()


@dataclass(slots=True)
class CreateRangeFilterFnHandler:
    """Handle the CreateRangeFilterFn command."""

    pipeline: AbstractPipeline

    def __call__(self, cmd: CreateRangeFilterFn) -> None:
        """Handle the CreateRangeFilterFn command."""
        if not cmd.is_enabled:
            return

        minimum, maximum = cmd.minimum, cmd.maximum

        def _get_range_filter() -> Callable[[int | float], bool]:
            if minimum >= 0 and maximum < float("inf"):
                return lambda v: minimum <= v <= maximum
            if minimum >= 0:
                return lambda v: v >= minimum
            if maximum < float("inf"):
                return lambda v: v <= maximum
            msg = "Invalid range filter configuration."
            raise ValueError(msg)

        self.pipeline.filters[cmd.name] = _get_range_filter()


@dataclass(slots=True)
class CreateFilefilterFnHandler:
    """Handle the CreateFilefilterFn command."""

    pipeline: AbstractPipeline

    def __call__(self, _: CreateFilefilterFn) -> None:
        """Handle the CreateFilefilterFn command."""

        def _generate_valid_filefilters() -> Iterator[Callable[[FSEntry], bool]]:
            for name, fn in self.pipeline.filters.items():
                yield _get_filefilter(name, fn)

        def _get_filefilter(name: str, fn: Callable) -> Callable[[FSEntry], bool]:
            match name:
                case FilterName.DIRNAME:
                    return lambda e, fn=fn: fn(e.parent)
                case FilterName.KEYWORD:
                    return lambda e, fn=fn: fn(e.stem)
                case FilterName.EXTENSION:
                    return lambda e, fn=fn: fn(e.ext)
                case FilterName.FILESIZE:
                    return lambda e, fn=fn: fn(e.size)
                case FilterName.DURATION:
                    return lambda e, fn=fn: fn(get_duration(e.path))
                case _:
                    msg = f"Unknown filter name: {name}"
                    raise ValueError(msg)

        filter_fns = tuple(_generate_valid_filefilters())

        def _get_composite_filefilter() -> Callable[[FSEntry], bool]:
            if filter_fns:
                if len(filter_fns) == 1:
                    return filter_fns[0]
                return lambda e: all(f(e) for f in filter_fns)
            return lambda _: True

        self.pipeline.filefilter_fn = _get_composite_filefilter()


####################
## EVENT HANDLERS ##
####################
@dataclass(slots=True)
class FileTransferredHandler:
    """Handle the FileTransferred event."""

    log_fn: Callable

    def __call__(self, event: FileTransferred) -> None:
        """Handle the FileTransferred event."""
        self.log_fn("%s: '%s' -> '%s'", event.count, event.src, event.dst)


@dataclass(slots=True)
class DirectoryTransferredHandler:
    """Handle the DirectoryTransferred event."""

    log_fn: Callable

    def __call__(self, event: DirectoryTransferred) -> None:
        """Handle the DirectoryTransferred event."""
        status = get_status(
            is_success=event.is_success,
            is_none_found_and_create_dir=event.is_empty_creation,
            is_stop_requested=event.is_stop_requested,
            is_root_locked=event.is_root_locked,
        )
        report = get_report(event.path, event.size, event.count, event.target_qty)
        self.log_fn("%s\n%s", status, report)
