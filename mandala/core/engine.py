"""Mandala Engine Module."""

import contextlib
import logging
import shutil
from dataclasses import dataclass, field
from time import perf_counter
from typing import TYPE_CHECKING

from ..utils import get_status_header

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from ..config import Filecount, Filename, Folder, SizeLimit
    from ..utils import DateTimeProvider, MandalaObserver
    from .quota import DiversityQuota
    from .reporter import ReportWriter
    from .validator import FileValidator
    from .walker import FSWalker


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class FolderStats:
    """Dataclass for Mandala state."""

    count: int = 0
    starttime: float = 0.0
    curr_size: int = 0
    total_size: int = 0

    def reset_for_folder(self) -> None:
        """Reset state variables for a new folder."""
        self.count = 0
        self.curr_size = 0
        self.starttime = perf_counter()

    def update_folder(self, size: int) -> None:
        """Update state on successful operation."""
        self.count += 1
        self.curr_size += size
        self.total_size += size


@dataclass(slots=True)
class MandalaEngine:
    """Core engine class for Mandala."""

    root: Path
    dry_run: bool
    validator: FileValidator
    reporter: ReportWriter
    quota: DiversityQuota
    walker: FSWalker
    timestamp: DateTimeProvider
    filecount: Filecount
    filename: Filename
    folder: Folder
    transfer: Callable
    folder_size_limit: SizeLimit
    total_size_limit: SizeLimit
    observer: MandalaObserver = field(init=False)
    folderstats: FolderStats = field(default_factory=FolderStats)
    stop_requested: bool = False

    def set_observer(self, observer: MandalaObserver) -> None:
        """Set the observer for the engine."""
        self.observer = observer

    def request_stop(self) -> None:
        """Request to stop the engine."""
        self.stop_requested = True

    def start(self) -> None:
        """Run the main file copying process."""
        self.observer.on_progress_total(self.folder.count)

        for _ in range(self.folder.count):
            target = self.filecount.get_count()
            dest = self.folder.create_dest_folder()

            if self.stop_requested:
                self._report("Process stopped by user request.")
                break

            self.process_folder(target, dest)

        self.observer.on_finished()

    def process_folder(self, target: int, dest: Path) -> None:
        """Run processing for a single folder."""
        self._prepare_folder(target, dest)
        self._transfer_folder(target, dest)
        self._finalize_folder(target, dest)

    def _prepare_folder(self, target: int, dest: Path) -> None:
        """Prepare state for processing a new folder."""
        self.timestamp.refresh()
        self.reporter.reset_for_dest(dest)
        self.observer.on_progress(target)
        self.quota.prepare_for_batch()
        self.folderstats.reset_for_folder()

    def _transfer_folder(self, target: int, dest: Path) -> None:
        """Process a single folder for file copying."""
        for entry in self.walker.walk():
            if self._is_stop_condition():
                break

            if entry is None or self.folderstats.count >= target:
                break

            path, size = entry.path, entry.size

            if not self.validator.is_valid(path, size):
                continue

            # Check if adding this file would exceed folder size limit
            if self.folder_size_limit.is_exceeded(self.folderstats.curr_size + size):
                self._report(msg=f"Folder size limit reached ({self.folder_size_limit.size_limit}B)")
                break

            # Check if adding this file would exceed total size limit
            if self.total_size_limit.is_exceeded(self.folderstats.total_size + size):
                self._report(msg=f"Total size limit reached ({self.total_size_limit.size_limit}B)")
                return

            if not self._transfer_file(path, dest):
                continue

            self.folderstats.update_folder(size)
            self.quota.register_success(path)
            self.observer.on_count(self.folderstats.count)
            self.observer.on_time()

    def _transfer_file(self, chosen: Path, dest: Path) -> bool:
        """Attempt to copy a file and return success status."""
        count = self.folderstats.count
        chosen_rel = chosen.relative_to(self.root)

        new_target_file = self.filename.calc_dest_target(chosen_rel, dest, count)
        if new_target_file is None:
            return False

        new_target_file_rel = new_target_file.relative_to(dest)
        copy_path_str = f"{chosen_rel} -> {new_target_file_rel}"

        if self.dry_run:
            self._report(msg=f"DRY: {count + 1}: {copy_path_str}")
            return True

        try:
            self.transfer(chosen, new_target_file)
        except (PermissionError, OSError):
            self._report(msg=f"FAILED: {copy_path_str}")
            logger.exception("Failed to copy file: %s", copy_path_str)
            return False
        else:
            self._report(msg=f"{count + 1}: {copy_path_str}")
            return True

    def _report(self, msg: str) -> None:
        """Report and log a message."""
        self.reporter.record_message(msg)
        self.observer.on_log(msg)

    def _is_stop_condition(self) -> bool:
        """Check if the process should stop based on conditions."""
        total_limit_exceeded = self.total_size_limit.is_exceeded(self.folderstats.total_size)
        return self.stop_requested or self.quota.all_locked() or total_limit_exceeded

    def _finalize_folder(self, target: int, dest: Path) -> None:
        """Create and write log at the end of folder."""
        self.observer.on_count_total()
        none_found = self.folderstats.count == 0 and self.folder.create_enabled
        status_prefix = get_status_header(
            success=(self.folderstats.count == target),
            stopped=self.stop_requested,
            none_found=none_found,
            all_searched=self.quota.all_locked(),
        )
        report = self.reporter.generate_report(
            status=f"{status_prefix}: {self.folderstats.count}/{target} files copied",
            runtime=round(perf_counter() - self.folderstats.starttime, 2),
            size=self.folderstats.curr_size,
        )
        self._report(report)
        self.reporter.save()
        self._remove_folder_if_empty(dest, none_found=none_found)

    def _remove_folder_if_empty(self, dest: Path, *, none_found: bool) -> None:
        """Remove the destination folder if it is empty."""
        if not none_found:
            return
        with contextlib.suppress(OSError):
            shutil.rmtree(dest)
