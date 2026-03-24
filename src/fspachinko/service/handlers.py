"""Handlers module."""

import logging
from dataclasses import dataclass
from functools import partial
from os import makedirs, scandir
from os.path import join
from random import randint
from typing import TYPE_CHECKING

from fspachinko.adapters.filenamer import TemplateFilenamer
from fspachinko.adapters.filesystemport import get_unique_path, remove_directory
from fspachinko.adapters.fswalker import FSWalker
from fspachinko.adapters.loggers import get_dest_log_filehandler
from fspachinko.adapters.media import get_duration
from fspachinko.adapters.transfer import FileTransferFnManager
from fspachinko.constants import FilterName
from fspachinko.domain.commands import (
    ProcessDirectory,
)
from fspachinko.domain.events import DirectoryStarted, ProcessStarted
from fspachinko.domain.model import DestinationDirectory, DiversityQuota, FSEntry, TransferJob
from fspachinko.helpers import get_report, get_status, get_text_patterns

if TYPE_CHECKING:
    from collections.abc import Callable

    from fspachinko.adapters.pipeline import AbstractPipeline
    from fspachinko.configuration.uow import AbstractConfigUnitOfWork
    from fspachinko.domain.commands import (
        CreateDestDirs,
        CreateFilefilterFn,
        CreateFilenameFn,
        CreateRangeFilterFn,
        CreateTextFilterFn,
        CreateTransferFn,
        CreateTransferJob,
        CreateWalkerFn,
        RunTransferJob,
        SaveProfile,
        SetPipelineCreateDir,
        SetRngSeed,
        StopProcess,
    )
    from fspachinko.domain.events import DirectoryTransferred, FileTransferred

    from .uow import AbstractTransferUnitOfWork


######################
## COMMAND HANDLERS ##
######################
@dataclass(slots=True)
class RunTransferJobHandler:
    """Handle the RunTransferJob command."""

    uow: AbstractTransferUnitOfWork
    pipeline: AbstractPipeline

    def __call__(self, cmd: RunTransferJob) -> None:
        """Handle the RunTransferJob command."""
        # Started
        with self.uow as uow:
            for dest_dir, target_qty in cmd.dest_dir_inputs:
                ProcessDirectoryHandler(uow=uow, pipeline=self.pipeline)(
                    ProcessDirectory(dest_dir=dest_dir, target_qty=target_qty)
                )
            uow.commit()
        # Finished


@dataclass(slots=True)
class CreateTransferJobHandler:
    """Handle the CreateTransferJob command."""

    uow: AbstractTransferUnitOfWork

    def __call__(self, cmd: CreateTransferJob) -> None:
        """Handle the CreateTransferJob command."""
        quota = DiversityQuota(cmd.root, cmd.max_per_dir, cmd.unique_files_only)
        job = TransferJob(quota=quota)
        with self.uow as uow:
            uow.repo.add(job)
            uow.commit()


@dataclass(slots=True)
class ProcessDirectoryHandler:
    """Handle the StartProcessingDirectory command."""

    uow: AbstractTransferUnitOfWork
    pipeline: AbstractPipeline

    def __call__(self, cmd: ProcessDirectory) -> None:
        """Handle the StartProcessingDirectory command."""
        dst = DestinationDirectory(cmd.dest_dir, cmd.target_qty)
        with self.uow as uow:
            handler = get_dest_log_filehandler(cmd.dest_dir)
            logging.getLogger().addHandler(handler)
            uow.repo.transfer_fn = self.pipeline.transfer_fn
            job = uow.repo.get()
            if job.is_stop_requested or job.is_root_locked:
                return
            job.reset()
            job.events.append(DirectoryStarted(target_qty=dst.target_qty))
            for entry in self.pipeline.walker_fn():
                if dst.is_success or job.is_stop_requested or job.is_root_locked:
                    break
                if not job.process_file(entry) or not self.pipeline.filefilter_fn(entry):
                    continue
                new_path = self.pipeline.get_new_path(dst=dst, e=entry)
                if new_path:
                    uow.repo.add_transfer(entry.path, new_path)
                    job.update(dst, entry, new_path)
            is_empty_creation = dst.is_none_found and self.pipeline.is_create_dir
            if is_empty_creation:
                remove_directory(dst.path)
            job.finalize_directory(dst, is_empty_creation=is_empty_creation)
            logging.getLogger().removeHandler(handler)
            handler.close()
            uow.commit()


@dataclass(slots=True)
class StopProcessHandler:
    """Handle the StopProcess command."""

    uow: AbstractTransferUnitOfWork

    def __call__(self, _: StopProcess) -> None:
        """Handle the StopProcess command."""
        job = self.uow.repo.get()
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
        self.pipeline.transfer_fn = FileTransferFnManager().get(cmd.transfermode)


@dataclass(slots=True)
class CreateFilenameFnHandler:
    """Handle the CreateFilenameFn command."""

    pipeline: AbstractPipeline

    def __call__(self, cmd: CreateFilenameFn) -> None:
        """Handle the CreateFilenameFn command."""
        if cmd.is_enabled:
            self.pipeline.filenamer_fn = TemplateFilenamer(cmd.template)
        else:
            self.pipeline.filenamer_fn = lambda e, _: e.stem


@dataclass(slots=True)
class CreateDestDirsHandler:
    """Handle the CreateDestDirs command."""

    pipeline: AbstractPipeline

    def __call__(self, cmd: CreateDestDirs) -> None:
        """Handle the CreateDestDirs command."""
        self.pipeline.dest_dir_inputs.clear()
        filecount_fn = (
            (lambda rnge=cmd.filecount_randrange: randint(*rnge))
            if cmd.filecount_rand_is_enabled
            else (lambda cnt=cmd.filecount_static: cnt)
        )
        if not cmd.directory_create_is_enabled:
            self.pipeline.dest_dir_inputs.append((cmd.directory_dest, filecount_fn()))
            return
        existing = {entry.path for entry in scandir(cmd.directory_dest) if entry.is_dir()}
        candidate = join(cmd.directory_dest, cmd.directory_name)
        while len(self.pipeline.dest_dir_inputs) < cmd.dir_count:
            next_name = get_unique_path(candidate, existing)
            makedirs(next_name, exist_ok=True)
            self.pipeline.dest_dir_inputs.append((next_name, filecount_fn()))
            existing.add(next_name)


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
            match len(patterns), should_include:
                case 1, True:
                    return lambda p: patterns[0].search(p) is not None
                case 1, False:
                    return lambda p: patterns[0].search(p) is None
                case _, True:
                    return lambda p: any(ptn.search(p) for ptn in patterns)
                case _, False:
                    return lambda p: not any(ptn.search(p) for ptn in patterns)
            return lambda _: True

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
            match minimum >= 0, maximum < float("inf"):
                case True, True:
                    return lambda v: minimum <= v <= maximum
                case True, False:
                    return lambda v: v >= minimum
                case False, True:
                    return lambda v: v <= maximum
            msg = "Invalid range filter configuration."
            raise ValueError(msg)

        self.pipeline.filters[cmd.name] = _get_range_filter()


FILTER_MAPPINGS: dict[str, Callable[[FSEntry, Callable], bool]] = {
    FilterName.DIRNAME: lambda e, fn: fn(e.parent),
    FilterName.KEYWORD: lambda e, fn: fn(e.stem),
    FilterName.EXTENSION: lambda e, fn: fn(e.ext),
    FilterName.FILESIZE: lambda e, fn: fn(e.size),
    FilterName.DURATION: lambda e, fn: fn(get_duration(e.path)),
}


@dataclass(slots=True)
class CreateFilefilterFnHandler:
    """Handle the CreateFilefilterFn command."""

    pipeline: AbstractPipeline

    def __call__(self, _: CreateFilefilterFn) -> None:
        """Handle the CreateFilefilterFn command."""

        def _build(name: str, fn: Callable) -> Callable[[FSEntry], bool]:
            if name not in FILTER_MAPPINGS:
                msg = f"Unknown filter name: {name}"
                raise ValueError(msg)
            return partial(FILTER_MAPPINGS[name], fn=fn)

        filter_fns = tuple(_build(name, fn) for name, fn in self.pipeline.filters.items())

        def _composite() -> Callable[[FSEntry], bool]:
            match len(filter_fns):
                case 0:
                    return lambda _: True
                case 1:
                    return filter_fns[0]
                case _:
                    return lambda e: all(f(e) for f in filter_fns)

        self.pipeline.filefilter_fn = _composite()


@dataclass(slots=True)
class SaveProfileHandler:
    """Handle the SaveProfile command."""

    uow: AbstractConfigUnitOfWork

    def __call__(self, cmd: SaveProfile) -> None:
        """Handle the SaveProfile command."""
        with self.uow as uow:
            uow.repo.set(cmd.path, cmd.config)
            uow.commit()


####################
## EVENT HANDLERS ##
####################


@dataclass(slots=True)
class ProcessStartedHandler:
    """Handle the ProcessStarted event."""

    log_fn: Callable

    def __call__(self, event: ProcessStarted) -> None:
        """Handle the ProcessStarted event."""
        self.log_fn("Process started with %d directories to process.", event.dir_count)


@dataclass(slots=True)
class FileTransferredHandler:
    """Handle the FileTransferred event."""

    log_fn: Callable

    def __call__(self, event: FileTransferred) -> None:
        """Handle the FileTransferred event."""
        self.log_fn("%s: '%s' -> '%s'", event.count, event.src, event.dst)


@dataclass(slots=True)
class DirectoryStartedHandler:
    """Handle the DirectoryStarted event."""

    log_fn: Callable

    def __call__(self, event: DirectoryStarted) -> None:
        """Handle the DirectoryStarted event."""
        self.log_fn("Processing directory with target quantity: %s", event.target_qty)


@dataclass(slots=True)
class DirectoryTransferredHandler:
    """Handle the DirectoryTransferred event."""

    log_fn: Callable

    def __call__(self, event: DirectoryTransferred) -> None:
        """Handle the DirectoryTransferred event."""
        status = get_status(
            success=event.is_success,
            empty_creation=event.is_empty_creation,
            stop_requested=event.is_stop_requested,
            root_locked=event.is_root_locked,
        )
        report = get_report(event.path, event.size, event.count, event.target_qty)
        self.log_fn("%s\n%s", status, report)
