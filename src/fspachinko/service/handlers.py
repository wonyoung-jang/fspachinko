"""Handlers module."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fspachinko.domain.model import DestinationDirectory, DiversityQuota, TransferJob

if TYPE_CHECKING:
    from collections import deque
    from collections.abc import Iterator

    from fspachinko.adapters.filesystem import AbstractFilesystem
    from fspachinko.adapters.loggers import AbstractLogger
    from fspachinko.adapters.pipeline import AbstractPipeline
    from fspachinko.domain.commands import RunTransferJob, SaveConfiguration, StopProcess
    from fspachinko.domain.events import DirectoryStarted, DirectoryTransferred, Event, FileTransferred
    from fspachinko.helpers import ReportWriter


##################################################################################
######## COMMAND HANDLERS ########################################################
##################################################################################
@dataclass(slots=True)
class RunTransferJobHandler:
    """Handle the RunTransferJob command."""

    job: TransferJob
    inputs: deque[tuple[str, int, bool]]
    filesystem: AbstractFilesystem
    pipeline: AbstractPipeline

    def __call__(self, cmd: RunTransferJob) -> Iterator[Event]:
        """Handle the RunTransferJob command.

        Side-effects/Outputs:
        - Destination directory may be created.
        - Destination logs may be created.
        - Files may be transferred.
        """
        self.job.is_stop_requested = False
        self.job.quota = DiversityQuota(cmd.root, cmd.max_per_dir, cmd.unique_files_only)
        for dst in self._iterate_inputs():
            if self.job.is_stop_condition:
                return
            yield self.job.start_directory(dst)
            yield from self._transfer_dir(dst)
            yield self.job.finalize_directory(dst)

    def _iterate_inputs(self) -> Iterator[DestinationDirectory]:
        """Iterate over the input destination directories."""
        while self.inputs:
            dest_dir, target_qty, should_create = self.inputs.popleft()
            dst = DestinationDirectory(path=dest_dir, target_qty=target_qty, should_create=should_create)
            if should_create:
                self.filesystem.make_directory(dest_dir)
            else:
                # Working with an existing dir, need to populate file tracking
                # to not overwrite existing files and keep track of stats
                for path, size in self.filesystem.get_existing_files_for_existing_dest(dest_dir):
                    dst.add(path, size)
            yield dst

    def _transfer_dir(self, dst: DestinationDirectory) -> Iterator[Event]:
        """Transfer files to a destination directory."""
        source = self.pipeline.walk()
        approved = (e for e in source if self.job.can_accept(e))
        filtered = (e for e in approved if self.pipeline.filter_file(e))
        mapped = ((e, self.pipeline.get_new_path(dst=dst, e=e)) for e in filtered)
        valid = ((e, newpath) for e, newpath in mapped if newpath is not None)
        for entry, newpath in valid:
            if dst.is_success or self.job.is_stop_condition:
                break
            self.pipeline.transfer_file(entry.path, newpath)
            yield self.job.register_transfer(dst, entry, newpath)


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


################################################################################
######## EVENT HANDLERS ########################################################
################################################################################


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

    filesystem: AbstractFilesystem
    logger: AbstractLogger
    reporter: type[ReportWriter]

    def __call__(self, evt: DirectoryTransferred) -> None:
        """Handle the DirectoryTransferred event."""
        path = evt.path
        is_empty_creation = evt.is_empty_creation
        report = self.reporter(
            path=path,
            size=evt.size,
            count=evt.count,
            target_qty=evt.target_qty,
            is_success=evt.is_success,
            is_empty_creation=is_empty_creation,
            is_stop_requested=evt.is_stop_requested,
            is_root_locked=evt.is_root_locked,
        )
        self.logger.info("%s", report)
        self.logger.remove_dest_log_filehandler(path)
        if is_empty_creation:
            self.filesystem.remove_directory(path)
