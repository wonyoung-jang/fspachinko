"""Engine Module."""

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


@dataclass(slots=True)
class JobRequest:
    """Dataclass for job request."""

    target: int
    dest: str


@dataclass(slots=True)
class JobRequestFactory:
    """Factory for creating job requests."""

    get_file_count: Callable[[], int]
    determine_dest_dirname: Callable[[], str]
    dir_count: int

    def create(self) -> JobRequest:
        """Create a job request based on the current configuration."""
        dest = self.determine_dest_dirname()
        if not exists(dest):
            mkdir(dest)
        return JobRequest(target=self.get_file_count(), dest=dest)

    def generate(self) -> list[JobRequest]:
        """Generate multiple job requests."""
        return [self.create() for _ in range(self.dir_count)]


@dataclass(slots=True)
class Engine:
    """Core engine class."""

    root: str
    context: EngineContext
    is_dry_run: bool
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
        for request in self.job_request_factory.generate():
            self.process_request(request)
        self.observer.on_finished()

    def process_request(self, request: JobRequest) -> None:
        """Run processing for a single folder."""
        self.observer.on_progress(request.target)
        self.context.prepare()
        self.context.setup_logger(request.dest)
        self.transfer_dir(request)
        self.log(msg=self.context.msg)
        self.log(msg=self.context.finalize(request))
        self.observer.on_count_total()

    def transfer_dir(self, request: JobRequest) -> None:
        """Process a single folder for file copying."""
        target, dest = request.target, request.dest
        curr_count = 0
        entries = self.entries
        while not self.context.should_stop(target):
            entry = next(entries)
            if self.transfer_file(entry, dest, curr_count):
                curr_count += 1
                self.context.update(entry)
                self.observer.on_count(curr_count)

    def transfer_file(self, entry: FSEntry, dest: str, curr_count: int) -> bool:
        """Attempt to copy a file and return success status."""
        new_filename = self.filename_fn(entry.path, dest, curr_count)
        if new_filename is None:
            return False

        msg = f"{curr_count + 1}: {relpath(entry, self.root)} -> {relpath(new_filename, dest)}"
        if self.is_dry_run:
            self.log(f"DRY - {msg}")
            return True

        try:
            self.transfer_fn(entry, new_filename)
            self.log(msg)
        except (PermissionError, OSError):
            self.log(f"FAILED - {msg}")
            return False
        return True

    def log(self, msg: str) -> None:
        """Report and log a message."""
        self.observer.on_log(msg)
        self.context.on_log(msg)
