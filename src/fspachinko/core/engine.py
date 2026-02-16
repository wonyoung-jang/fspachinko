"""Engine Module."""

import logging
from dataclasses import dataclass, field
from os import mkdir
from os.path import basename, exists, join, relpath
from time import perf_counter
from typing import TYPE_CHECKING

from .helpers import convert_byte_to_human_readable_size

if TYPE_CHECKING:
    import os
    from collections.abc import Callable, Iterator

    from .context import EngineContext
    from .observer import Observer
    from .walker import FSEntry

logger = logging.getLogger(__name__)


def get_dest_log_filehandler(dest: str) -> logging.FileHandler:
    """Set up a logger for the job request."""
    report_path = join(dest, f"!_{basename(dest)}_report.log")
    formatter = logging.Formatter("[%(asctime)s] %(message)s", datefmt="%H:%M:%S")
    handler = logging.FileHandler(report_path, mode="a", encoding="utf-8", delay=True)
    handler.setLevel(logging.INFO)
    handler.setFormatter(formatter)
    return handler


@dataclass(slots=True)
class JobRequest:
    """Dataclass for job request."""

    target: int
    dest: str
    file_count: int = 0
    curr_size: int = 0
    start_time: float = field(default_factory=perf_counter)

    def __post_init__(self) -> None:
        """Post-initialization tasks."""
        if not exists(self.dest):
            mkdir(self.dest)

    def update(self, size: int) -> None:
        """Update the job request state."""
        self.file_count += 1
        self.curr_size += size

    @property
    def runtime_str(self) -> str:
        """Get the runtime as a formatted string."""
        return f"{perf_counter() - self.start_time:.2f}s"

    @property
    def size_str(self) -> str:
        """Get the current size as a human-readable string."""
        return convert_byte_to_human_readable_size(self.curr_size)


@dataclass(slots=True)
class JobRequestFactory:
    """Factory for creating job requests."""

    get_file_count: Callable[[], int]
    determine_dest_dirname: Callable[[], str]
    dir_count: int

    def generate(self) -> Iterator[JobRequest]:
        """Generate multiple job requests."""
        yield from (
            JobRequest(
                target=self.get_file_count(),
                dest=self.determine_dest_dirname(),
            )
            for _ in range(self.dir_count)
        )


@dataclass(slots=True)
class Engine:
    """Core engine class."""

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
        self.observer.on_total_start(self.job_request_factory.dir_count)
        for dir_i, request in enumerate(self.job_request_factory.generate(), start=1):
            self.observer.on_directory_start(request.target)
            self.context.prepare()
            log_handler = get_dest_log_filehandler(request.dest)
            root_logger = logging.getLogger()
            root_logger.addHandler(log_handler)

            self.transfer_dir(request)

            logger.info(self.context.generate_report_header(request))
            self.context.finalize(request)
            root_logger.removeHandler(log_handler)
            self.observer.on_directory_increment(dir_i)
        self.observer.on_finished()

    def transfer_dir(self, request: JobRequest) -> None:
        """Process a single folder for file copying."""
        count = 0
        while not self.context.should_stop(request):
            entry = next(self.entries, None)
            if entry is None:
                break

            new_filename = self.filename_fn(entry.path, request.dest, count)
            if new_filename is None:
                continue

            msg = f"{count + 1}: {relpath(entry, self.context.root)} -> {relpath(new_filename, request.dest)}"

            if not self.context.is_dry_run:
                try:
                    self.transfer_fn(entry, new_filename)
                except PermissionError, OSError:
                    logger.info("FAILED - %s", msg)
                    continue

            logger.info(msg)
            self.context.update(entry)
            request.update(entry.size)
            count += 1
            self.observer.on_file_increment(count)
