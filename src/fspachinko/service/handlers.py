"""Handlers module."""

import logging
from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..domain.commands import StartProcess, StopProcess
from ..domain.events import (
    DirectoryLogged,
    DirectoryStarted,
    Event,
    FileTransferLogged,
    FileTransferred,
    ProcessStarted,
    ProcessStopped,
)
from ..domain.model import DestinationDirectory, DiversityQuota
from ..helpers import get_status

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from ..adapters.loggers import AbstractLoggingPort
    from ..adapters.pipeline import TransferPipeline
    from ..domain.commands import Command
    from .uow import AbstractUnitOfWork

logger = logging.getLogger(__name__)


def start_process(_: StartProcess, uow: AbstractUnitOfWork) -> Iterator[Event | Command]:
    """Handle the StartProcessCommand."""
    with uow:
        yield from uow.engine.start_process()
        uow.commit()


def stop_process(_: StopProcess, uow: AbstractUnitOfWork) -> None:
    """Handle the StopProcessCommand."""
    with uow:
        uow.engine.stop_engine()
        uow.commit()


COMMAND_HANDLERS: dict[type[Command], Callable] = {
    StartProcess: start_process,
    StopProcess: stop_process,
}


def handle_process_started(event: ProcessStarted, _: AbstractUnitOfWork) -> None:
    """Handle the StartProcessEvent."""
    logger.debug("%s", event)


def handle_directory_started(event: DirectoryStarted, _: AbstractUnitOfWork) -> None:
    """Handle the DirectoryStartEvent."""
    logger.debug("%s", event)


def handle_file_transferred(event: FileTransferred, _: AbstractUnitOfWork) -> None:
    """Handle the FileTransferredEvent."""
    logger.debug("%s", event)


def handle_finished(event: ProcessStopped, __: AbstractUnitOfWork) -> None:
    """Handle the FinishedEvent."""
    logger.debug("%s", event)


def handle_file_transfer_logged(event: FileTransferLogged, _: AbstractUnitOfWork) -> None:
    """Handle the FileTransferLogged event."""
    logger.info("%s: %s -> %s", event.count, event.src, event.dst)


def handle_directory_logged(event: DirectoryLogged, _: AbstractUnitOfWork) -> None:
    """Handle the DirectoryLogged event."""
    logger.info("%s\n%s", event.status, event.report)


EVENT_HANDLERS: dict[type[Event], list[Callable]] = {
    ProcessStarted: [handle_process_started],
    DirectoryStarted: [handle_directory_started],
    FileTransferred: [handle_file_transferred],
    ProcessStopped: [handle_finished],
    FileTransferLogged: [handle_file_transfer_logged],
    DirectoryLogged: [handle_directory_logged],
}


@dataclass(slots=True)
class Engine:
    """Core engine class."""

    dir_count: int
    is_create_dir: bool
    pipeline: TransferPipeline
    logging: AbstractLoggingPort
    quota: DiversityQuota
    is_stop_requested: bool = False
    events: deque[Event | Command] = field(default_factory=deque)

    def start_process(self) -> Iterator[Event | Command]:
        """Process."""
        yield ProcessStarted(dir_count=self.dir_count)

        for di in range(1, self.dir_count + 1):
            if self.is_stop_requested:
                break
            target_qty = self.pipeline.get_file_count()
            yield from self.process_dir(di=di, target_qty=target_qty)

        yield ProcessStopped()

    def process_dir(self, di: int, target_qty: int) -> Iterator[Event | Command]:
        """Process."""
        yield DirectoryStarted(di, target_qty)
        dst = DestinationDirectory(
            path=self.pipeline.get_currdir_dest(),
            target_qty=target_qty,
        )
        self.quota.reset()
        self.logging.add_handler(dst.path)

        entries = self.pipeline.walk()
        while not self.is_stop_condition(dst) and (e := next(entries, None)) is not None:
            if not self.quota.can_accept(e):
                continue

            if not self.pipeline.filter_file(e):
                continue

            newpath = self.pipeline.get_new_path(dst=dst, e=e)
            if newpath is None:
                continue

            try:
                self.pipeline.transfer_file(e.path, newpath)  # I/O
            except PermissionError, OSError, FileNotFoundError:
                continue

            self.quota.update(e)
            dst.accept(e)
            yield FileTransferLogged(count=dst.count, src=e.path, dst=newpath)
            yield FileTransferred(count=dst.count)

        is_none_found_and_create_dir = dst.is_none_found and self.is_create_dir
        status = get_status(
            is_success=dst.is_success,
            is_none_found_and_create_dir=is_none_found_and_create_dir,
            is_stop_requested=self.is_stop_requested,
            is_root_locked=self.quota.is_root_locked,
        )
        yield DirectoryLogged(status=status, report=dst.report_str)
        self.pipeline.remove_dst_dir_if_empty(
            dst.path,
            none_found=is_none_found_and_create_dir,
        )

        self.logging.remove_handler()

    def is_stop_condition(self, dst: DestinationDirectory) -> bool:
        """Check if the stop condition is met."""
        return dst.is_success or self.is_stop_requested or self.quota.is_root_locked

    def stop_engine(self) -> None:
        """Stop the engine."""
        self.is_stop_requested = True
