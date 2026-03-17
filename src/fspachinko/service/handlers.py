"""Handlers module."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..adapters.filesystemport import remove_directory
from ..domain.events import DirectoryTransferred, Event, FileTransferred
from ..domain.model import DestinationDirectory
from ..helpers import get_report, get_status

if TYPE_CHECKING:
    from collections.abc import Callable

    from ..domain.commands import Command, StartProcessingDirectory, StopProcess
    from .uow import AbstractUnitOfWork


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

            for entry in self.uow.pipeline.walk():
                if job.dst.is_success or job.is_stop_requested or job.is_root_locked:
                    break

                if not job.process_file(entry) or not self.uow.pipeline.filter_file(entry):
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
@dataclass(slots=True)
class FileTransferredHandler:
    """Handle the FileTransferred event."""

    call: Callable

    def __call__(self, event: FileTransferred) -> None:
        """Handle the FileTransferred event."""
        self.call("%s: %s -> %s", event.count, event.src, event.dst)


@dataclass(slots=True)
class DirectoryTransferredHandler:
    """Handle the DirectoryTransferred event."""

    call: Callable

    def __call__(self, event: DirectoryTransferred) -> None:
        """Handle the DirectoryTransferred event."""
        self.call("%s\n%s", event.status, event.report)
