"""Engine Module."""

import logging
from dataclasses import dataclass, field
from os import makedirs
from os.path import exists, relpath
from time import perf_counter
from typing import TYPE_CHECKING

from .helpers import convert_byte_to_human_readable_size, get_new_fpath
from .loggers import get_dest_log_filehandler

if TYPE_CHECKING:
    from collections.abc import Iterator

    from fspachinko.core.walker import FSWalker

    from .context import Context, DateTimeStamp, DiversityQuota
    from .dirname import DirectoryNamer
    from .filecount import FileCountGenerator
    from .filefilter import FileFilter
    from .filenamer import Filenamer
    from .observer import Observer
    from .transfer import Transfer
    from .walker import FSEntry

logger = logging.getLogger(__name__)


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

    filecount_fn: FileCountGenerator
    dirname_fn: DirectoryNamer
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

    context: Context
    job_factory: JobRequestFactory
    filterer: FileFilter
    filenamer: Filenamer
    transfer: Transfer
    walker: FSWalker
    quota: DiversityQuota
    dtstamp: DateTimeStamp
    observer: Observer
    _entries: Iterator[FSEntry] = field(init=False)

    def __post_init__(self) -> None:
        """Post-initialization tasks."""
        self._entries = self.walker()

    def start(self) -> None:
        """Run the main file copying process."""
        self.observer.on_start_process(self.job_factory.dir_count)
        for request in self.job_factory.generate():
            self.process(request)
        self.observer.on_finished()

    def process(self, request: JobRequest) -> None:
        """Process a single folder for file copying."""
        self.observer.on_directory_start(request.idx, request.target)
        self.dtstamp.reset()
        self.quota.reset()
        log_handler = get_dest_log_filehandler(request.dest)
        logger.addHandler(log_handler)

        while not self.context.should_stop(request, self.quota):
            if (e := next(self._entries, None)) is None:
                break

            if self.quota.is_file_locked(e):
                continue

            self.quota.lock_file(e)

            if self.quota.is_dir_locked_from_file(e) or not self.filterer(e):
                continue

            newstem = self.filenamer(e, request, self.dtstamp)
            if (newname := get_new_fpath(request.dest, e.path, newstem, e.ext)) is None:
                continue

            try:
                self.transfer(e, newname)
            except PermissionError, OSError:
                continue

            msg = f"{request.file_count + 1}: {relpath(e.path, self.context.root)} -> {relpath(newname, request.dest)}"
            logger.info(msg)
            self.quota.update(e)
            request.update(e.size)
            self.observer.on_file_transferred(request.file_count)

        summary = self.context.generate_summary(request, self.dtstamp.date_time_report_str)
        logger.info(summary)
        logger.removeHandler(log_handler)
        log_handler.close()
        self.context.finalize(request, self.quota)

    def request_stop(self) -> None:
        """Request to stop the engine."""
        self.context.is_stop_requested = True
