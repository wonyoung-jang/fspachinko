"""Mandala Engine Module."""

from __future__ import annotations

import contextlib
import logging
import shutil
from dataclasses import dataclass, field
from time import perf_counter
from typing import TYPE_CHECKING

from ..utils.helpers import get_status_header

if TYPE_CHECKING:
    from pathlib import Path

    from ..config.config import Filecount, Filename, Folder
    from ..utils.interfaces import MandalaObserver
    from .quota import DiversityQuota
    from .reporter import ReportWriter
    from .timestamp import DateTimeProvider
    from .transfer import Transfer
    from .validator import FileValidator
    from .walker import RandomFSWalker


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class MandalaState:
    """Dataclass for Mandala state."""

    count: int = 0
    size: int = 0
    starttime: float = 0.0

    def reset_for_folder(self) -> None:
        """Reset state variables for a new folder."""
        self.count = 0
        self.size = 0
        self.starttime = perf_counter()

    def update_folder(self, size: int) -> None:
        """Update state on successful operation."""
        self.count += 1
        self.size += size


@dataclass(slots=True)
class MandalaEngine:
    """Core engine class for Mandala."""

    root: Path
    dry_run: bool
    validator: FileValidator
    reporter: ReportWriter
    quota: DiversityQuota
    walker: RandomFSWalker
    timestamp: DateTimeProvider
    filecount: Filecount
    filename: Filename
    folder: Folder
    transfer: Transfer
    observer: MandalaObserver = field(init=False)
    _state: MandalaState = field(default_factory=MandalaState)
    _request_stop: bool = False

    def set_observer(self, observer: MandalaObserver) -> None:
        """Set the observer for the engine."""
        self.observer = observer

    def request_stop(self) -> None:
        """Request to stop the engine."""
        self._request_stop = True

    def start(self) -> None:
        """Run the main file copying process."""
        self.observer.on_progress_total(self.folder.count)

        for _ in range(self.folder.count):
            target = self.filecount.get_count()
            dest = self.folder.create_dest_folder()

            if self._request_stop:
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
        self._state.reset_for_folder()

    def _transfer_folder(self, target: int, dest: Path) -> None:
        """Process a single folder for file copying."""
        for entry in self.walker.walk():
            if self._is_stop_condition():
                break

            if entry is None or self._state.count >= target:
                break

            path, size = entry.path, entry.size

            if not self.validator.is_valid(path, size):
                continue

            if not self._transfer_file(path, dest):
                continue

            self._state.update_folder(size)
            self.quota.register_success(path)
            self.observer.on_count(self._state.count)
            self.observer.on_time()

    def _transfer_file(self, chosen: Path, dest: Path) -> bool:
        """Attempt to copy a file and return success status."""
        count = self._state.count
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
            self.transfer.transfer(chosen, new_target_file)
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
        return self._request_stop or self.quota.all_locked()

    def _finalize_folder(self, target: int, dest: Path) -> None:
        """Create and write log at the end of folder."""
        count = self._state.count

        self.observer.on_count_total()

        none_found = count == 0 and self.folder.create_enabled

        status_prefix = get_status_header(
            success=(count == target),
            stopped=self._request_stop,
            none_found=none_found,
            all_searched=self.quota.all_locked(),
        )

        report = self.reporter.generate_report(
            status=f"{status_prefix}: {count}/{target} files copied",
            runtime=round(perf_counter() - self._state.starttime, 2),
            size=self._state.size,
        )
        self._report(report)
        self.reporter.save()

        if none_found:
            with contextlib.suppress(OSError):
                shutil.rmtree(dest)
