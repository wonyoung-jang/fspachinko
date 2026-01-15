"""Mandala Engine Module."""

from __future__ import annotations

import contextlib
import shutil
from dataclasses import dataclass, field
from time import perf_counter
from typing import TYPE_CHECKING

from .helpers import calc_dest_file_path, create_dest_folder, get_status_header, trash_path

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path
    from random import Random

    from ..config.interfaces import MandalaObserver
    from .config import MandalaConfig
    from .quota import DiversityQuota
    from .reporter import ReportWriter
    from .state import MandalaState
    from .validator import FileValidator
    from .walker import RandomFSWalker


@dataclass(slots=True)
class MandalaEngine:
    """Core engine class for Mandala."""

    config: MandalaConfig
    state: MandalaState
    validator: FileValidator
    reporter: ReportWriter
    stop_requested: bool
    rng: Random
    quota: DiversityQuota
    walker: RandomFSWalker
    observer: MandalaObserver = field(init=False)

    def set_observer(self, observer: MandalaObserver) -> None:
        """Set the observer for the engine."""
        self.observer = observer

    def request_stop(self) -> None:
        """Request to stop the engine."""
        self.stop_requested = True

    def start(self) -> None:
        """Run the main file copying process."""
        clear_history = not self.config.folder.unique

        for target in self._generate_folder_target_counts():
            if self.stop_requested:
                break

            self.state.reset_for_folder()
            self.quota.prepare_for_batch(clear_history=clear_history)
            self.process_folder(target)
            self.observer.on_count_total()

        self.observer.on_finished()

    def process_folder(self, target: int) -> None:
        """Process a single folder for file copying."""
        dest_dir = create_dest_folder(self.config.folder, self.config.dest)
        self.reporter.reset_for_dest(dest_dir)
        self.observer.on_progress(target)

        count = 0

        for candidate in self.walker.generate_candidates():
            if self._is_stop_condition() or candidate is None or count >= target:
                break

            path, size = candidate.path, candidate.size

            if self.validator.is_valid(path, size) and self._try_copy(path, dest_dir, count):
                count += 1
                self.quota.register_success(path)
                self.state.update_success(size)

                self.observer.on_count(count)
                self.observer.on_time()

                trash_path(path, condition=self.config.trash.source_file)
            else:
                msg = f"INVALID: {path.relative_to(self.config.root)}"
                self._report_invalid(msg)
                trash_path(path, condition=self.config.trash.invalid_file)

        self._finalize_folder(dest_dir, count, target)

    def _try_copy(self, chosen: Path, dest: Path, count: int) -> bool:
        """Attempt to copy a file and return success status."""
        target = calc_dest_file_path(self.config.filename, chosen, dest, count)
        if target is None:
            return False

        chosen_rel = chosen.relative_to(self.config.root)
        target_rel = target.relative_to(self.config.dest)
        if self.config.execution.dry_run:
            msg = f"DRY RUN: {count + 1}: {chosen_rel} -> {target_rel}"
            self._report(msg)
            return True

        try:
            shutil.copy2(chosen, target)
        except (PermissionError, OSError):
            msg = f"FAILED COPY: {chosen_rel} -> {target_rel}"
            self._report(msg)
            return False
        else:
            msg = f"{count + 1}: {chosen_rel} -> {target_rel}"
            self._report(msg)
            return True

    def _report(self, msg: str) -> None:
        """Report and log a message."""
        self.reporter.record_message(msg)
        self.observer.on_log(msg)

    def _report_invalid(self, msg: str) -> None:
        """Report invalid file message if logging is enabled."""
        if self.config.execution.log_invalid:
            self._report(msg)

    def _generate_folder_target_counts(self) -> Iterator[int]:
        """Prepare target file counts for each folder."""
        folder_count = self.config.folder.count
        self.observer.on_progress_total(folder_count)
        for _ in range(folder_count):
            if self.config.filecount.is_rand_count:
                yield self.rng.randint(
                    self.config.filecount.count_min_rand,
                    self.config.filecount.count_max_rand,
                )
            else:
                yield self.config.filecount.count

    def _is_stall_timeout(self) -> bool:
        """Check if the process has timed out based on stall time."""
        return (perf_counter() - self.state.start_time) > self.config.progress.stall_time_limit

    def _is_stop_condition(self) -> bool:
        """Check if the process should stop based on conditions."""
        return self.stop_requested or self.quota.all_locked() or self._is_stall_timeout()

    def _finalize_folder(self, dest: Path, count: int, target: int) -> None:
        """Create and write log at the end of folder."""
        runtime = round(perf_counter() - self.state.start_currdir, 2)
        copied = f"{count}/{target} files copied"
        create_folders = self.config.folder.create
        none_found = count == 0 and create_folders
        prefix = get_status_header(
            success=(count == target),
            stopped=self.stop_requested,
            none_found=none_found,
            timeout=self._is_stall_timeout(),
            all_searched=self.quota.all_locked(),
        )
        status = f"{prefix}: {copied}"

        report = self.reporter.generate_report(dest, status, runtime)
        self._report(report)
        self.reporter.save()

        if none_found:
            with contextlib.suppress(OSError):
                shutil.rmtree(dest)
