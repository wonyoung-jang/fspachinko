"""Engine Module."""

from dataclasses import dataclass, field
from os.path import relpath
from typing import TYPE_CHECKING

from .walker import FSEntry

if TYPE_CHECKING:
    import os
    from collections.abc import Callable

    from ..config import Filename
    from ..utils import Observer
    from .destination import JobRequest, JobRequestFactory
    from .state import EngineContext
    from .validator import FileValidator
    from .walker import FSWalker


@dataclass(slots=True)
class Engine:
    """Core engine class."""

    root: str
    walker: FSWalker
    validator: FileValidator
    filename: Filename
    do_transfer_strategy: Callable[[os.PathLike, str], None]
    context: EngineContext
    job_request_factory: JobRequestFactory
    observer: Observer = field(init=False)

    def set_observer(self, observer: Observer) -> None:
        """Set the observer for the engine."""
        self.observer: Observer = observer

    def request_stop(self) -> None:
        """Request to stop the engine."""
        self.context.is_stop_requested = True

    def start(self) -> None:
        """Run the main file copying process."""
        self.observer.on_progress_total(self.job_request_factory.dir_count)
        for request in self.job_request_factory.generate():
            self.process_directory(request)
        self.observer.on_finished()

    def process_directory(self, request: JobRequest) -> None:
        """Run processing for a single folder."""
        target, dest = request.target, request.dest
        self.observer.on_progress(target)
        self.context.prepare(dest)
        self.transfer_directory(request)
        self.report(self.context.finalize(target, dest))
        self.observer.on_count_total()

    def transfer_directory(self, request: JobRequest) -> None:
        """Process a single folder for file copying."""
        target, dest = request.target, request.dest
        if self.context.should_stop(target):
            self.report(msg=self.context.msg)
            return

        for entry in self.walker.walk():
            if entry is None:
                break

            fsentry = FSEntry.from_direntry(entry)
            if not self.validator.is_valid(fsentry):
                continue

            if not self.transfer_file(fsentry, dest):
                continue

            self.context.update(fsentry)
            self.observer.on_count(self.context.dirstat.count)
            self.observer.on_time()

            if self.context.should_stop(target):
                self.report(msg=self.context.msg)
                return

    def transfer_file(self, entry: os.PathLike, dest: str) -> bool:
        """Attempt to copy a file and return success status."""
        count = self.context.dirstat.count
        chosen_rel = relpath(entry, self.root)
        chosen_new = self.filename.determine_dest_filename(chosen_rel, dest, count)
        if chosen_new is None:
            return False

        msg = f"{count + 1}: {chosen_rel} -> {relpath(chosen_new, dest)}"

        if self.context.is_dry_run:
            self.report(f"DRY - {msg}")
            return True

        try:
            self.do_transfer_strategy(entry, chosen_new)
        except (PermissionError, OSError):
            self.report(f"FAILED - {msg}")
            return False

        self.report(msg)
        return True

    def report(self, msg: str) -> None:
        """Report and log a message."""
        self.observer.on_log(msg)
        self.context.reporter.record(msg)
