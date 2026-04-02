"""Handlers module."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fspachinko.domain.model import DestinationDirectory, DiversityQuota, TransferJob

if TYPE_CHECKING:
    from collections import deque
    from collections.abc import Callable

    from fspachinko.adapters.filesystem import AbstractFilesystem
    from fspachinko.adapters.loggers import AbstractLogger
    from fspachinko.adapters.pipeline import AbstractPipeline
    from fspachinko.domain.commands import ProcessDirectory, RunTransferJob, SaveConfiguration, StopProcess
    from fspachinko.domain.events import DirectoryStarted, DirectoryTransferred, FileTransferred


######################
## COMMAND HANDLERS ##
######################
@dataclass(slots=True)
class RunTransferJobHandler:
    """Handle the RunTransferJob command."""

    job: TransferJob
    inputs: deque[tuple[str, int, bool]]

    def __call__(self, cmd: RunTransferJob) -> None:
        """Handle the RunTransferJob command."""
        self.job.quota = DiversityQuota(cmd.root, cmd.max_per_dir, cmd.unique_files_only)
        while self.inputs:
            dest_dir, target_qty, should_create = self.inputs.popleft()
            self.job.dir_ready_to_process(dest_dir, target_qty, should_create=should_create)


@dataclass(slots=True)
class ProcessDirectoryHandler:
    """Handle the StartProcessingDirectory command."""

    job: TransferJob
    filesystem: AbstractFilesystem
    pipeline: AbstractPipeline

    def __call__(self, cmd: ProcessDirectory) -> None:
        """Handle the StartProcessingDirectory command.

        Side-effects/Outputs:
        - Destination directory may be created.
        - Destination logs may be created.
        - Files may be transferred.
        """
        dst = DestinationDirectory(path=cmd.dest_dir, target_qty=cmd.target_qty, should_create=cmd.should_create)
        if dst.should_create:
            self.filesystem.make_directory(dst.path)
        if self.job.is_stop_requested or self.job.is_root_locked:
            return
        self.job.reset()
        self.job.start_directory(dst)
        for entry in self.pipeline.walk():
            if dst.is_success or self.job.is_stop_requested or self.job.is_root_locked:
                break
            if not (
                self.job.can_accept(entry)
                and self.pipeline.filter_file(entry)
                and (new_path := self.pipeline.get_new_path(dst=dst, e=entry))
            ):
                continue
            try:
                self.pipeline.transfer_file(entry.path, new_path)
            except OSError:
                continue
            self.job.register_transfer(dst, entry, new_path)
        self.job.finalize_directory(dst)


@dataclass(slots=True)
class StopProcessHandler:
    """Handle the StopProcess command."""

    job: TransferJob

    def __call__(self, _: StopProcess) -> None:
        """Handle the StopProcess command."""
        self.job.request_stop()


@dataclass(slots=True)
class SaveProfileHandler:
    """Handle the SaveProfile command."""

    filesystem: AbstractFilesystem

    def __call__(self, cmd: SaveConfiguration) -> None:
        """Handle the SaveProfile command."""
        self.filesystem.save_json(cmd.path, cmd.config)


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
            stop_requested=evt.is_stop_requested,
            empty_creation=evt.is_empty_creation,
            root_locked=evt.is_root_locked,
        )
        report = self.get_report(evt.path, evt.size, evt.count, evt.target_qty)
        self.logger.info("%s\n%s", status, report)
        self.logger.remove_dest_log_filehandler(evt.path)
        if evt.is_empty_creation:
            self.filesystem.remove_directory(evt.path)
