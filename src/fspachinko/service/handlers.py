"""Handlers module."""

import logging
from typing import TYPE_CHECKING

from ..domain.commands import StartProcess, StartProcessingDirectory, StopProcess
from ..domain.events import (
    DirectoryLogged,
    DirectoryStarted,
    Event,
    FileTransferLogged,
    FileTransferred,
    ProcessStarted,
    ProcessStopped,
)
from ..domain.model import DestinationDirectory
from ..helpers import get_status

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from ..domain.commands import Command
    from .uow import AbstractUnitOfWork

logger = logging.getLogger(__name__)

type Message = Command | Event


def start_process(cmd: StartProcess, uow: AbstractUnitOfWork) -> Iterator[Message]:
    """Handle the StartProcessCommand."""
    yield ProcessStarted(dir_count=cmd.dir_count)
    for di in range(1, cmd.dir_count + 1):
        target_qty = uow.pipeline.get_file_count()
        yield StartProcessingDirectory(di=di, target_qty=target_qty)
    yield ProcessStopped()


def stop_process(_: StopProcess, uow: AbstractUnitOfWork) -> None:
    """Handle the StopProcessCommand."""
    uow.job.request_stop()


def process_directory(cmd: StartProcessingDirectory, uow: AbstractUnitOfWork) -> Iterator[Message]:
    """Handle the ProcessDirectoryCommand."""
    with uow:
        job = uow.job
        pipeline = uow.pipeline

        if job.is_stop_requested or job.quota.is_root_locked:
            return

        yield DirectoryStarted(idx=cmd.di, target=cmd.target_qty)

        dst = DestinationDirectory(path=pipeline.get_currdir_dest(), target_qty=cmd.target_qty)
        job.quota.reset()
        pipeline.add_handler(dst.path)

        for e in pipeline.walk():
            if dst.is_success or job.is_stop_requested or job.quota.is_root_locked:
                break
            if not job.process_file(e):
                continue
            if not pipeline.is_valid(e):
                continue
            new_path = pipeline.get_new_path(dst=dst, e=e)
            if new_path:
                uow.register_transfer(e.path, new_path)
                job.update(dst, e)
                yield FileTransferLogged(count=dst.count, src=e.path, dst=new_path)

        is_empty_creation = dst.is_none_found and pipeline.is_create_dir
        pipeline.remove_dst_dir_if_empty(dst.path, none_found=is_empty_creation)
        pipeline.remove_handler()
        status = get_status(
            is_success=dst.is_success,
            is_none_found_and_create_dir=is_empty_creation,
            is_stop_requested=job.is_stop_requested,
            is_root_locked=job.quota.is_root_locked,
        )
        yield DirectoryLogged(status=status, report=dst.report_str)

        uow.commit()


COMMAND_HANDLERS: dict[type[Command], Callable] = {
    StartProcess: start_process,
    StopProcess: stop_process,
    StartProcessingDirectory: process_directory,
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
