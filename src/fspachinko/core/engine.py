"""Engine Module."""

import logging
from dataclasses import dataclass, field
from os import makedirs
from os.path import basename, exists, join, relpath
from time import perf_counter
from typing import TYPE_CHECKING

from .helpers import convert_byte_to_human_readable_size, get_new_fpath

if TYPE_CHECKING:
    import os
    from collections.abc import Callable, Iterator

    from .config import Filenamer
    from .context import DateTimeStamp, DiversityQuota, EngineContext
    from .filefilter import FileFilter
    from .observer import Observer
    from .walker import FSEntry

logger = logging.getLogger(__name__)


def get_dest_log_filehandler(dest: str) -> logging.FileHandler:
    """Set up a logger for the job request."""
    report_path = join(dest, f"!_{basename(dest)}_report.log")
    handler = logging.FileHandler(report_path, mode="a", encoding="utf-8", delay=True)
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("[%(asctime)s] %(message)s", datefmt="%H:%M:%S"))
    return handler


@dataclass(slots=True)
class JobRequest:
    """Dataclass for job request."""

    idx: int
    target: int
    dest: str
    file_count: int = 0
    curr_size: int = 0
    start_time: float = field(default_factory=perf_counter)

    def __post_init__(self) -> None:
        """Post-initialization tasks."""
        if not exists(self.dest):
            makedirs(self.dest, exist_ok=True)

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

    filecount_fn: Callable[[], int]
    dirname_fn: Callable[[], str]
    dir_count: int

    def generate(self) -> Iterator[JobRequest]:
        """Generate multiple job requests."""
        yield from (
            JobRequest(
                idx=idx,
                target=self.filecount_fn(),
                dest=self.dirname_fn(),
            )
            for idx in range(1, self.dir_count + 1)
        )


@dataclass(slots=True)
class Engine:
    """Core engine class."""

    context: EngineContext
    filterer: FileFilter
    filenamer: Filenamer
    transferer: Callable[[os.PathLike, str], None]
    job_factory: JobRequestFactory
    entries: Iterator[FSEntry]
    quota: DiversityQuota
    dtstamp: DateTimeStamp
    observer: Observer

    def start(self) -> None:
        """Run the main file copying process."""
        self.observer.on_start_process(self.job_factory.dir_count)
        for request in self.job_factory.generate():
            self.process(request)
        self.observer.on_finished()

    def process(self, r: JobRequest) -> None:
        """Process a single folder for file copying."""
        self.observer.on_directory_start(r.idx, r.target)
        self.dtstamp.reset()
        self.quota.reset()
        log_handler = get_dest_log_filehandler(r.dest)
        logger.addHandler(log_handler)

        while not self.context.should_stop(r, self.quota):
            if (e := next(self.entries, None)) is None:
                break
            if self.quota.is_file_locked(e):
                continue
            self.quota.lock_file(e)
            if self.quota.is_dir_locked(e) or not self.filterer(e):
                continue
            new_stem = self.filenamer(e, r, self.dtstamp)
            new_filename = get_new_fpath(r.dest, e.path, new_stem, e.ext)
            if new_filename is None:
                continue
            logmsg = f"{r.file_count + 1}: {relpath(e, self.context.root)} -> {relpath(new_filename, r.dest)}"
            if not self.context.is_dry_run:
                try:
                    self.transferer(e, new_filename)
                except PermissionError, OSError:
                    logger.info("FAILED - %s", logmsg)
                    continue
            logger.info(logmsg)
            self.quota.update(e)
            r.update(e.size)
            self.observer.on_file_transferred(r.file_count)

        logger.info(self.context.generate_report_header(r, self.dtstamp.date_time_report_str))
        logger.removeHandler(log_handler)
        log_handler.close()
        self.context.finalize(r, self.quota)

    def request_stop(self) -> None:
        """Request to stop the engine."""
        self.context.is_stop_requested = True
