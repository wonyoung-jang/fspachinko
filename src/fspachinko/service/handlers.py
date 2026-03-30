"""Handlers module."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fspachinko.domain.commands import ProcessDirectory
from fspachinko.domain.model import DestinationDirectory, DiversityQuota, TransferJob

if TYPE_CHECKING:
    from collections.abc import Callable

    from fspachinko.adapters.filesystem import AbstractFilesystem
    from fspachinko.adapters.loggers import AbstractLogger
    from fspachinko.adapters.pipeline import AbstractPipeline
    from fspachinko.configuration.uow import AbstractConfigUnitOfWork
    from fspachinko.domain.commands import CreateTransferJob, RunTransferJob, SaveConfiguration, StopProcess
    from fspachinko.domain.events import DirectoryStarted, DirectoryTransferred, FileTransferred
    from fspachinko.service.uow import AbstractTransferUnitOfWork


######################
## COMMAND HANDLERS ##
######################
@dataclass(slots=True)
class RunTransferJobHandler:
    """Handle the RunTransferJob command."""

    uow: AbstractTransferUnitOfWork
    pipeline: AbstractPipeline

    def __call__(self, _: RunTransferJob) -> None:
        """Handle the RunTransferJob command."""
        while self.pipeline.dest_dir_inputs:
            dest_dir_input = self.pipeline.dest_dir_inputs.popleft()
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
        with self.uow as uow:
            quota = DiversityQuota(
                root=cmd.root,
                max_per_dir=cmd.max_per_dir,
                unique_files_only=cmd.unique_files_only,
            )
            job = TransferJob(quota=quota)
            uow.repo.add(job)
            uow.commit()


@dataclass(slots=True)
class ProcessDirectoryHandler:
    """Handle the StartProcessingDirectory command."""

    uow: AbstractTransferUnitOfWork
    pipeline: AbstractPipeline

    def __call__(self, cmd: ProcessDirectory) -> None:
        """Handle the StartProcessingDirectory command."""
        with self.uow as uow:
            dst = DestinationDirectory(path=cmd.dest_dir, target_qty=cmd.target_qty)
            job = uow.repo.get()
            if job.is_stop_requested or job.is_root_locked:
                return
            job.reset()
            job.start_directory(dst)
            valid_transfers = job.determine_transfers(dst=dst, pipeline=self.pipeline)
            for entry, new_path in valid_transfers:
                uow.repo.add_transfer(entry.path, new_path)
                job.update_file(dst, entry, new_path)
            job.finalize_directory(dst, is_empty_creation=(dst.is_none_found and self.pipeline.is_create_dir))
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


####################
## EVENT HANDLERS ##
####################


@dataclass(slots=True)
class FileTransferredHandler:
    """Handle the FileTransferred event."""

    logger: AbstractLogger

    def __call__(self, evt: FileTransferred) -> None:
        """Handle the FileTransferred event."""
        self.logger.info("%s: '%s' -> '%s'", evt.count, evt.src, evt.dst)


@dataclass(slots=True)
class DirectoryStartedHandler:
    """Handle the DirectoryStarted event."""

    logger: AbstractLogger

    def __call__(self, evt: DirectoryStarted) -> None:
        """Handle the DirectoryStarted event."""
        self.logger.add_dest_log_filehandler(evt.path)
        self.logger.info("Processing directory %s with target quantity: %s", evt.path, evt.target_qty)


@dataclass(slots=True)
class DirectoryTransferredHandler:
    """Handle the DirectoryTransferred event."""

    get_status: Callable
    get_report: Callable
    filesystem: AbstractFilesystem
    logger: AbstractLogger

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
        self.logger.info("%s\n%s", status, report)
        self.logger.remove_dest_log_filehandler(evt.path)
        if evt.is_empty_creation:
            self.filesystem.remove_directory(evt.path)
