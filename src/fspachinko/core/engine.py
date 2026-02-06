"""Engine Module."""

import logging
import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from line_profiler import profile

from .walker import FSEntry

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from ..config import Filecount, Filename
    from ..utils import Observer
    from .state import Context
    from .validator import FileValidator
    from .walker import FSWalker


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class Engine:
    """Core engine class."""

    root: str
    walker: FSWalker
    validator: FileValidator
    filecount: Filecount
    filename: Filename
    do_transfer_strategy: Callable[[os.PathLike, str], None]
    context: Context
    folder_count: int
    is_create_unique_folders: bool
    observer: Observer = field(init=False)

    def set_observer(self, observer: Observer) -> None:
        """Set the observer for the engine."""
        self.observer = observer

    def request_stop(self) -> None:
        """Request to stop the engine."""
        self.context.is_stop_requested = True

    def start(self) -> None:
        """Run the main file copying process."""
        self.observer.on_progress_total(self.folder_count)
        for target, dest in self.get_transfer_parameters():
            if not self.is_create_unique_folders:
                self.walker.reset()
            self.process_directory(target, dest)
        self.observer.on_finished()

    def get_transfer_parameters(self) -> Iterator[tuple[int, str]]:
        """Get transfer parameters for all folders."""
        for _ in range(self.folder_count):
            yield (
                self.filecount.get_file_count(),
                self.context.folder.determine_dest_dirname(),
            )

    def process_directory(self, target: int, dest: str) -> None:
        """Run processing for a single folder."""
        os.mkdir(dest)
        self.observer.on_progress(target)
        self.context.prepare(dest)
        self.transfer_directory(target, dest)
        self.observer.on_count_total()
        self.report(self.context.finalize(target, dest))

    @profile
    def transfer_directory(self, target: int, dest: str) -> None:
        """Process a single folder for file copying."""
        if self.context.should_stop(target):
            self.report_state()
            return

        for entry in self.walker.walk():
            if entry is None:
                break

            if self.context.should_stop(target):
                self.report_state()
                return

            fsentry = FSEntry.from_direntry(entry)
            if not self.validator.is_valid(fsentry):
                continue

            if not self.transfer_file(fsentry, dest):
                continue

            self.context.update_on_success(fsentry)
            self.update_observer_on_entry()

    def transfer_file(self, entry: os.PathLike, dest: str) -> bool:
        """Attempt to copy a file and return success status."""
        count = self.context.dirstat.count
        chosen_rel = os.path.relpath(entry, self.root)
        chosen_new = self.filename.determine_dest_filename(chosen_rel, dest, count)
        if chosen_new is None:
            return False

        msg = f"{count + 1}: {chosen_rel} -> {os.path.relpath(chosen_new, dest)}"

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

    def report_state(self) -> None:
        """Report the current engine state."""
        self.report(msg=self.context.msg)

    def report(self, msg: str) -> None:
        """Report and log a message."""
        self.observer.on_log(msg)
        self.context.reporter.record(msg)

    def update_observer_on_entry(self) -> None:
        """Update observer with current entry statistics."""
        self.observer.on_count(self.context.dirstat.count)
        self.observer.on_time()
