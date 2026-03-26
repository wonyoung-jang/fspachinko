"""Handlers module."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fspachinko.constants import FilterName
from fspachinko.domain.commands import ProcessDirectory
from fspachinko.domain.model import DestinationDirectory, DiversityQuota, FSEntry, TransferJob

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
    from fspachinko.domain.events import DirectoryStarted, DirectoryTransferred, FileTransferred

    from .uow import AbstractTransferUnitOfWork


######################
## COMMAND HANDLERS ##
######################
@dataclass(slots=True)
class RunTransferJobHandler:
    """Handle the RunTransferJob command."""

    uow: AbstractTransferUnitOfWork
    pipeline: AbstractPipeline
    remove_directory: Callable

    def __call__(self, _cmd: RunTransferJob) -> None:
        """Handle the RunTransferJob command."""
        job = self.uow.repo.get()
        for dest_dir, target_qty in job.dest_dir_inputs:
            ProcessDirectoryHandler(uow=self.uow, pipeline=self.pipeline, remove_directory=self.remove_directory)(
                ProcessDirectory(dest_dir=dest_dir, target_qty=target_qty)
            )


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
    remove_directory: Callable

    def __call__(self, cmd: ProcessDirectory) -> None:
        """Handle the StartProcessingDirectory command."""
        dst = DestinationDirectory(path=cmd.dest_dir, target_qty=cmd.target_qty)
        with self.uow as uow:
            uow.repo.transfer_fn = self.pipeline.transfer_fn
            job = uow.repo.get()
            if job.is_stop_requested or job.is_root_locked:
                return
            job.reset()
            job.start_directory(dst)
            for entry in self.pipeline.walker_fn():
                if dst.is_success or job.is_stop_requested or job.is_root_locked:
                    break
                if not job.process_file(entry) or not self.pipeline.filefilter_fn(entry):
                    continue
                new_path = self.pipeline.get_new_path(dst=dst, e=entry)
                if new_path:
                    uow.repo.add_transfer(entry.path, new_path)
                    job.update_file(dst, entry, new_path)
            is_empty_creation = dst.is_none_found and self.pipeline.is_create_dir
            if is_empty_creation:
                self.remove_directory(dst.path)
            job.finalize_directory(dst, is_empty_creation=is_empty_creation)
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
    transfer_fn_getter: Callable

    def __call__(self, cmd: CreateTransferFn) -> None:
        """Handle the CreateTransferFn command."""
        self.pipeline.transfer_fn = self.transfer_fn_getter(cmd.transfermode)


@dataclass(slots=True)
class CreateFilenameFnHandler:
    """Handle the CreateFilenameFn command."""

    pipeline: AbstractPipeline
    template_filenamer: Callable

    def __call__(self, cmd: CreateFilenameFn) -> None:
        """Handle the CreateFilenameFn command."""
        if cmd.is_enabled:
            self.pipeline.filenamer_fn = self.template_filenamer(cmd.template)
        else:
            self.pipeline.filenamer_fn = lambda e, _: e.stem


@dataclass(slots=True)
class CreateDestDirsHandler:
    """Handle the CreateDestDirs command."""

    uow: AbstractTransferUnitOfWork
    get_unique_path: Callable
    randcount_fn: Callable
    make_directory: Callable
    get_existing_directories: Callable
    join_path: Callable

    def __call__(self, cmd: CreateDestDirs) -> None:
        """Handle the CreateDestDirs command."""
        job = self.uow.repo.get()
        job.dest_dir_inputs.clear()
        filecount_fn = (
            (lambda rnge=cmd.filecount_randrange: self.randcount_fn(*rnge))
            if cmd.filecount_rand_is_enabled
            else (lambda cnt=cmd.filecount_static: cnt)
        )
        if not cmd.directory_create_is_enabled:
            job.dest_dir_inputs.append((cmd.directory_dest, filecount_fn()))
            return
        existing = self.get_existing_directories(cmd.directory_dest)
        candidate = self.join_path(cmd.directory_dest, cmd.directory_name)
        while len(job.dest_dir_inputs) < cmd.dir_count:
            next_name = self.get_unique_path(candidate, existing)
            self.make_directory(next_name)
            job.dest_dir_inputs.append((next_name, filecount_fn()))
            existing.add(next_name)


@dataclass(slots=True)
class CreateWalkerFnHandler:
    """Handle the CreateWalkerFn command."""

    pipeline: AbstractPipeline
    walker: Callable

    def __call__(self, cmd: CreateWalkerFn) -> None:
        """Handle the CreateWalkerFn command."""
        self.pipeline.walker_fn = self.walker(root=cmd.root, should_follow_symlink=cmd.should_follow_symlink)


@dataclass(slots=True)
class CreateTextFilterFnHandler:
    """Handle the CreateTextFilterFn command."""

    pipeline: AbstractPipeline
    get_text_patterns: Callable

    def __call__(self, cmd: CreateTextFilterFn) -> None:
        """Handle the CreateTextFilterFn command."""
        if not (cmd.is_enabled and cmd.text):
            return

        should_include = cmd.should_include
        patterns = self.get_text_patterns(cmd.text, cmd.re_fmt)

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


@dataclass(slots=True)
class CreateFilefilterFnHandler:
    """Handle the CreateFilefilterFn command."""

    pipeline: AbstractPipeline
    get_duration: Callable

    def __call__(self, _: CreateFilefilterFn) -> None:
        """Handle the CreateFilefilterFn command."""
        filter_mapping: dict[str, Callable[[FSEntry, Callable], bool]] = {
            FilterName.DIRNAME: lambda e, fn: fn(e.parent),
            FilterName.KEYWORD: lambda e, fn: fn(e.stem),
            FilterName.EXTENSION: lambda e, fn: fn(e.ext),
            FilterName.FILESIZE: lambda e, fn: fn(e.size),
            FilterName.DURATION: lambda e, fn: fn(self.get_duration(e.path)),
        }

        def _build(name: str, fn: Callable) -> Callable[[FSEntry], bool]:
            if name not in filter_mapping:
                msg = f"Unknown filter name: {name}"
                raise ValueError(msg)
            return lambda e, fn=fn: filter_mapping[name](e, fn)

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
class FileTransferredHandler:
    """Handle the FileTransferred event."""

    log_fn: Callable

    def __call__(self, evt: FileTransferred) -> None:
        """Handle the FileTransferred event."""
        self.log_fn("%s: '%s' -> '%s'", evt.count, evt.src, evt.dst)


@dataclass(slots=True)
class DirectoryStartedHandler:
    """Handle the DirectoryStarted event."""

    log_fn: Callable
    add_log_file: Callable

    def __call__(self, evt: DirectoryStarted) -> None:
        """Handle the DirectoryStarted event."""
        self.add_log_file(evt.path)
        self.log_fn("Processing directory %s with target quantity: %s", evt.path, evt.target_qty)


@dataclass(slots=True)
class DirectoryTransferredHandler:
    """Handle the DirectoryTransferred event."""

    log_fn: Callable
    remove_log_file: Callable
    get_status: Callable
    get_report: Callable

    def __call__(self, evt: DirectoryTransferred) -> None:
        """Handle the DirectoryTransferred event."""
        status = self.get_status(
            success=evt.is_success,
            empty_creation=evt.is_empty_creation,
            stop_requested=evt.is_stop_requested,
            root_locked=evt.is_root_locked,
        )
        report = self.get_report(
            evt.path,
            evt.size,
            evt.count,
            evt.target_qty,
        )
        self.log_fn("%s\n%s", status, report)
        self.remove_log_file(evt.path)
