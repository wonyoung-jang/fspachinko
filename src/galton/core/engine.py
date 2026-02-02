"""Engine Module."""

import logging
import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

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
    do_transfer_strategy: Callable[[str, str], None]
    context: Context
    observer: Observer = field(init=False)

    def set_observer(self, observer: Observer) -> None:
        """Set the observer for the engine."""
        self.observer = observer

    def request_stop(self) -> None:
        """Request to stop the engine."""
        self.context.is_stop_requested = True

    def start(self) -> None:
        """Run the main file copying process."""
        folder_count = self.context.folder.count
        self.observer.on_progress_total(folder_count)
        for _ in range(folder_count):
            self.process_directory()
        self.observer.on_finished()

    def process_directory(self) -> None:
        """Run processing for a single folder."""
        target = self.filecount.get_file_count()
        dest = self.context.folder.determine_dest_dirname()
        os.mkdir(dest)
        self.observer.on_progress(target)
        self.context.prepare(dest)
        self.transfer_directory(target, dest)
        self.observer.on_count_total()
        self.report(self.context.finalize(target, dest))

    def transfer_directory(self, target: int, dest: str) -> None:
        """Process a single folder for file copying."""
        if self.context.should_stop(target):
            self.report_state()
            return

        for entry in self.walker.walk():
            if entry is None:
                continue

            if self.context.should_stop(target):
                self.report_state()
                return

            path, size = entry.path, entry.stat().st_size
            if not self.validator.is_valid(path, size):
                self.context.quota.lock_file(entry)
                continue

            if not self.transfer_file(path, dest):
                self.context.quota.lock_file(entry)
                continue

            self.context.update_on_success(path, size)
            self.update_observer_on_entry()

    def transfer_file(self, chosen: str, dest: str) -> bool:
        """Attempt to copy a file and return success status."""
        count = self.context.folderstats.count
        chosen_rel = os.path.relpath(chosen, self.root)
        chosen_new = self.filename.determine_dest_filename(chosen_rel, dest, count)
        if chosen_new is None:
            return False

        msg = f"{count + 1}: {chosen_rel} -> {os.path.relpath(chosen_new, dest)}"

        if self.context.should_treat_as_dry_run(msg):
            self.report_state()
            return True

        try:
            self.do_transfer_strategy(chosen, chosen_new)
        except (PermissionError, OSError):
            self.context.set_errored(msg)
            self.report_state()
            return False

        self.context.set_transferred(msg)
        self.report_state()
        return True

    def report_state(self) -> None:
        """Report the current engine state."""
        self.report(msg=self.context.state.message)

    def report(self, msg: str) -> None:
        """Report and log a message."""
        self.observer.on_log(msg)
        self.context.reporter.record_message(msg)

    def update_observer_on_entry(self) -> None:
        """Update observer with current entry statistics."""
        self.observer.on_count(self.context.folderstats.count)
        self.observer.on_time()
