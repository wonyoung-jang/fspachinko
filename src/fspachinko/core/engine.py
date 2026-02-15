"""Engine Module."""

import logging
from dataclasses import dataclass
from os import mkdir
from os.path import exists, relpath
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import os
    from collections.abc import Callable, Iterator

    from .context import EngineContext
    from .observer import Observer
    from .walker import FSEntry

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class JobRequest:
    """Dataclass for job request."""

    target: int
    dest: str

    def __post_init__(self) -> None:
        """Post-initialization tasks."""
        if not exists(self.dest):
            mkdir(self.dest)


@dataclass(slots=True)
class JobRequestFactory:
    """Factory for creating job requests."""

    get_file_count: Callable[[], int]
    determine_dest_dirname: Callable[[], str]
    dir_count: int

    def generate(self) -> list[JobRequest]:
        """Generate multiple job requests."""
        return [
            JobRequest(
                target=self.get_file_count(),
                dest=self.determine_dest_dirname(),
            )
            for _ in range(self.dir_count)
        ]


@dataclass(slots=True)
class Engine:
    """Core engine class."""

    root: str
    context: EngineContext
    filename_fn: Callable[[str, str, int], str | None]
    transfer_fn: Callable[[os.PathLike, str], None]
    job_request_factory: JobRequestFactory
    entries: Iterator[FSEntry]
    observer: Observer

    def request_stop(self) -> None:
        """Request to stop the engine."""
        self.context.is_stop_requested = True

    def start(self) -> None:
        """Run the main file copying process."""
        self.observer.on_progress_total(self.job_request_factory.dir_count)
        for i, request in enumerate(self.job_request_factory.generate(), start=1):
            self.process_request(request)
            self.observer.on_count_total(i)
        self.observer.on_finished()

    def process_request(self, request: JobRequest) -> None:
        """Run processing for a single folder."""
        self.observer.on_progress(request.target)
        self.context.prepare()
        self.context.setup_logger(request.dest)
        self.transfer_dir(request)
        self.log(msg=self.context.msg)
        self.log(msg=self.context.generate_report_header(request))
        self.context.finalize(request)

    def transfer_dir(self, request: JobRequest) -> None:
        """Process a single folder for file copying."""
        target, dest = request.target, request.dest
        count = 0
        while not self.context.should_stop(target):
            entry = next(self.entries, None)
            if entry is None:
                break

            new_filename = self.filename_fn(entry.path, dest, count)
            if new_filename is None:
                continue

            msg = f"{count + 1}: {relpath(entry, self.root)} -> {relpath(new_filename, dest)}"

            if not self.context.is_dry_run:
                try:
                    self.transfer_fn(entry, new_filename)
                except PermissionError, OSError:
                    self.log(f"FAILED - {msg}")
                    continue

            self.log(msg)
            count += 1
            self.context.update(entry)
            self.observer.on_count(count)

    def log(self, msg: str) -> None:
        """Report and log a message."""
        logger.info(msg)
        self.context.on_log(msg)
