"""Engine Module."""

from dataclasses import dataclass, field
from os.path import relpath
from typing import TYPE_CHECKING

from .walker import FSEntry

if TYPE_CHECKING:
    import os
    from collections.abc import Callable

    from ..core import Filename, Observer
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
        self.context.prepare(request.dest)

        self.transfer_dir(request)

        finalized_msg = self.context.finalize(request)
        self.report(finalized_msg)
        self.observer.on_count_total()

    def transfer_dir(self, request: JobRequest) -> None:
        """Process a single folder for file copying."""
        target, dest = request.target, request.dest
        if self.context.should_stop(target):
            self.report(msg=self.context.msg)
            return

        curr_count = 0
        for entry in self.walker.walk():
            if entry is None:
                break

            fsentry = FSEntry.from_direntry(entry)
            if not self.validator.is_valid(fsentry):
                continue

            if not self.transfer_file(fsentry, dest, curr_count):
                continue

            curr_count += 1
            self.context.update(fsentry)
            self.observer.on_count(curr_count)
            self.observer.on_time()

            if self.context.should_stop(target):
                self.report(msg=self.context.msg)
                return

    def transfer_file(self, entry: FSEntry, dest: str, count: int) -> bool:
        """Attempt to copy a file and return success status."""
        chosen_rel = relpath(entry.path, self.root)
        chosen_new = self.filename.determine_dest_filename(chosen_rel, dest, count)
        if chosen_new is None:
            return False

        msg = f"{count + 1}: {chosen_rel}\n    ↳{relpath(chosen_new, dest)}"

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
