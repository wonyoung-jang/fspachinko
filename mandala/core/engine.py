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
    from collections.abc import Iterator
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

    bytes_in_currdir: int = 0
    start_time_currdir: float = 0.0

    def reset_for_folder(self) -> None:
        """Reset state variables for a new folder."""
        self.bytes_in_currdir = 0
        _start = perf_counter()
        self.start_time_currdir = _start

    def update_success(self, size: int) -> None:
        """Update state on successful operation."""
        self.bytes_in_currdir += size


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

        for target, dest in self._generate_target_and_dest():
            if self._request_stop:
                break

            self.process_folder(target, dest)

        self.observer.on_finished()

    def process_folder(self, target: int, dest: Path) -> None:
        """Run processing for a single folder."""
        self._prep_folder(target, dest)
        copied = self._copy_folder(target, dest)
        self._complete_folder(dest, copied, target)

    def _prep_folder(self, target: int, dest: Path) -> None:
        """Prepare state for processing a new folder."""
        self.timestamp.refresh()
        self.reporter.reset_for_dest(dest)
        self.observer.on_progress(target)
        self.quota.prepare_for_batch()
        self._state.reset_for_folder()

    def _copy_folder(self, target: int, dest: Path) -> int:
        """Process a single folder for file copying."""
        copied = 0

        for candidate in self.walker.generate_candidates():
            if self._is_stop_condition() or candidate is None or copied >= target:
                break

            path, size = candidate.path, candidate.size

            if self.validator.is_valid(path, size) and self._copy_file_attempt(path, dest, copied):
                copied += 1
                self._state.update_success(size)
                self.quota.register_success(path)
                self.observer.on_count(copied)
                self.observer.on_time()

        return copied

    def _complete_folder(self, dest: Path, copied: int, target: int) -> None:
        """Post-process actions after folder processing."""
        self.observer.on_count_total()
        self._finalize_folder(dest, copied, target)

    def _copy_file_attempt(self, chosen: Path, dest: Path, count: int) -> bool:
        """Attempt to copy a file and return success status."""
        chosen_rel = chosen.relative_to(self.root)

        target = self.filename.calc_dest_target(chosen_rel, dest, count)
        if target is None:
            return False

        target_rel = target.relative_to(dest)
        copy_path_str = f"{chosen_rel} -> {target_rel}"

        if self.dry_run:
            self._report(msg=f"DRY: {count + 1}: {copy_path_str}")
            return True

        try:
            self.transfer.transfer(chosen, target)
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

    def _generate_target_and_dest(self) -> Iterator[tuple[int, Path]]:
        """Prepare target file counts for each folder."""
        for _ in range(self.folder.count):
            yield self.filecount.get_count(), self.folder.create_dest_folder()

    def _is_stop_condition(self) -> bool:
        """Check if the process should stop based on conditions."""
        return self._request_stop or self.quota.all_locked()

    def _finalize_folder(self, dest: Path, count: int, target: int) -> None:
        """Create and write log at the end of folder."""
        runtime = round(perf_counter() - self._state.start_time_currdir, 2)
        copied = f"{count}/{target} files copied"
        create_folders = self.folder.create_enabled
        none_found = count == 0 and create_folders
        prefix = get_status_header(
            success=(count == target),
            stopped=self._request_stop,
            none_found=none_found,
            all_searched=self.quota.all_locked(),
        )
        status = f"{prefix}: {copied}"

        report = self.reporter.generate_report(dest, status, runtime, self._state.bytes_in_currdir)
        self._report(report)
        self.reporter.save()

        if none_found:
            with contextlib.suppress(OSError):
                shutil.rmtree(dest)
