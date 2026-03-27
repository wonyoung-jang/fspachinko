"""Handlers module."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fspachinko.domain.commands import BootstrapConfig, ProcessDirectory
from fspachinko.domain.model import DestinationDirectory, DiversityQuota, TransferJob

if TYPE_CHECKING:
    from collections.abc import Callable

    from fspachinko.adapters.pipeline import AbstractPipeline
    from fspachinko.configuration.uow import AbstractConfigUnitOfWork
    from fspachinko.domain.commands import CreateTransferJob, RunTransferJob, SaveConfiguration, StopProcess
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

    def __call__(self, _cmd: RunTransferJob) -> None:
        """Handle the RunTransferJob command."""
        while self.pipeline.dest_dir_inputs:
            dest_dir_input = self.pipeline.dest_dir_inputs.pop(0)
            dest_dir, target_qty = dest_dir_input
            handler = ProcessDirectoryHandler(
                uow=self.uow,
                pipeline=self.pipeline,
            )
            handler(ProcessDirectory(dest_dir=dest_dir, target_qty=target_qty))


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
                self.pipeline.remove_directory(dst.path)
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
class SaveProfileHandler:
    """Handle the SaveProfile command."""

    uow: AbstractConfigUnitOfWork

    def __call__(self, cmd: SaveConfiguration) -> None:
        """Handle the SaveProfile command."""
        with self.uow as uow:
            uow.repo.set(cmd.path, cmd.config)
            uow.commit()


@dataclass(slots=True)
class BootstrapConfigHandler:
    """Bootstrapper for translating configuration into commands."""

    pipeline: AbstractPipeline
    rng_seed_fn: Callable
    transfer_fn_getter: Callable
    template_filenamer: Callable
    walker: Callable
    get_existing_directories: Callable
    join_path: Callable
    get_unique_path: Callable
    make_directory: Callable
    randcount_fn: Callable
    get_text_patterns: Callable
    get_duration: Callable
    config_to_file_filter: Callable

    def __call__(self, cmd: BootstrapConfig) -> None:
        """Translate the configuration into commands."""
        c = cmd.config
        self.rng_seed_fn(c.options.rng_seed)
        self.pipeline.is_create_dir = c.directory.is_enabled
        self.pipeline.transfer_fn = self.transfer_fn_getter(c.options.transfer_mode)
        if c.filename.is_enabled:
            self.pipeline.filenamer_fn = self.template_filenamer(c.filename.template)
        else:
            self.pipeline.filenamer_fn = lambda e, _: e.stem
        self.pipeline.walker_fn = self.walker(root=c.root, should_follow_symlink=c.options.should_follow_symlink)
        filecount_fn = (
            (lambda rnge=(c.filecount.rand_min, c.filecount.rand_max): self.randcount_fn(*rnge))
            if c.filecount.is_rand_enabled
            else (lambda count=c.filecount.count: count)
        )
        if not c.directory.is_enabled:
            self.pipeline.dest_dir_inputs.append((c.dest, filecount_fn()))
            return
        existing = self.get_existing_directories(c.dest)
        candidate = self.join_path(c.dest, c.directory.name)
        while len(self.pipeline.dest_dir_inputs) < c.directory.count:
            next_name = self.get_unique_path(candidate, existing)
            self.make_directory(next_name)
            self.pipeline.dest_dir_inputs.append((next_name, filecount_fn()))
            existing.add(next_name)
        config_to_file_filter = self.config_to_file_filter(
            get_text_patterns=self.get_text_patterns,
            get_duration=self.get_duration,
        )
        self.pipeline.filefilter_fn = config_to_file_filter(c)


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
