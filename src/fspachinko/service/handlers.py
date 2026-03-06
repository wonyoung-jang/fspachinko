"""Handlers module."""

import logging
from typing import TYPE_CHECKING

from ..domain.commands import StartProcess, StopProcess
from ..domain.events import DirectoryStarted, Event, FileTransferred, ProcessStarted, ProcessStopped

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from ..domain.commands import Command
    from .uow import AbstractUnitOfWork

logger = logging.getLogger(__name__)


def start_process(_: StartProcess, uow: AbstractUnitOfWork) -> Iterator:
    """Handle the StartProcessCommand."""
    with uow:
        yield from uow.engine.process()
        uow.commit()


def stop_process(_: StopProcess, uow: AbstractUnitOfWork) -> None:
    """Handle the StopProcessCommand."""
    with uow:
        uow.engine.is_stop_requested = True
        uow.commit()


def handle_process_started(event: ProcessStarted, _: AbstractUnitOfWork) -> None:
    """Handle the StartProcessEvent."""
    logger.debug("Starting process:  with %s directories to transfer.", event.dir_count)


def handle_directory_started(event: DirectoryStarted, _: AbstractUnitOfWork) -> None:
    """Handle the DirectoryStartEvent."""
    logger.debug("Starting directory %s with target %s files.", event.idx, event.target)


def handle_file_transferred(event: FileTransferred, _: AbstractUnitOfWork) -> None:
    """Handle the FileTransferredEvent."""
    logger.debug("Transferred file %s.", event.count)


def handle_finished(_: ProcessStopped, __: AbstractUnitOfWork) -> None:
    """Handle the FinishedEvent."""
    logger.debug("Processing finished.")


EVENT_HANDLERS: dict[type[Event], list[type[AbstractHandler]]] = {
    ProcessStarted: [ProcessStartedHandler],
    DirectoryStarted: [DirectoryStartedHandler],
    FileTransferred: [FileTransferredHandler],
    ProcessStopped: [ProcessStoppedHandler],
    FileTransferLogged: [FileTransferLoggedHandler],
    DirectoryLogged: [DirectoryLoggedHandler],
}
