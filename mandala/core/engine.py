"""Mandala Engine Module."""

from __future__ import annotations

import contextlib
import shutil
from dataclasses import dataclass, field
from time import perf_counter
from typing import TYPE_CHECKING

from .helpers import calc_dest_file_path, trash_path

if TYPE_CHECKING:
    from pathlib import Path
    from random import Random

    from .config import MandalaConfig
    from .interfaces import MandalaObserver
    from .logger import MandalaLogger
    from .quota import DiversityQuota
    from .state import MandalaState
    from .validator import FileValidator
    from .walker import RandomFSWalker


@dataclass(slots=True)
class MandalaEngine:
    """Core engine class for Mandala."""

    config: MandalaConfig
    state: MandalaState
    validator: FileValidator
    logger: MandalaLogger
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
        clear_history = not self.config.folders_model.unique
        target_counts = self._prepare_folder_targets()

        for target in target_counts:
            if self.stop_requested:
                break

            self.state.reset_for_folder()
            self.quota.prepare_for_batch(clear_history=clear_history)
            self.process_folder(target)
            self.observer.on_count_total()

        self.observer.on_finished()

    def process_folder(self, target: int) -> None:
        """Process a single folder for file copying."""
        dest_dir = self._create_dest_folder()
        self.logger.reset_for_dest(dest_dir)
        self.observer.on_progress(target)

        count = 0

        for candidate in self.walker.generate_candidates():
            if candidate is None or count >= target or self._is_stop_condition():
                break

            path = candidate.path
            size = candidate.size

            if not self.validator.is_valid(path, size):
                self._handle_invalid(path)
                continue

            if self._try_copy(path, dest_dir, count):
                count += 1
                self.quota.register_success(path)
                self.state.update_success(size)

                self.observer.on_count(count)
                self.observer.on_time()

                trash_path(path, condition=self.config.trash_model.source_file)
            else:
                self._handle_invalid(path)

        self._finalize_folder(dest_dir, count, target)

    def _try_copy(self, chosen: Path, dest: Path, count: int) -> bool:
        """Attempt to copy a file and return success status."""
        target = calc_dest_file_path(self.config.filename_model, chosen, dest, count)
        if target is None:
            return False

        if self.config.execution_model.dry_run:
            msg = f"DRY RUN: {count + 1}: {chosen} -> {target}"
            self.logger.log_message(msg)
            self.observer.on_log(msg)
            return True

        try:
            shutil.copy2(chosen, target)
        except (PermissionError, OSError):
            self.logger.log_message(f"Failed to copy: {chosen} -> {target}")
            self.observer.on_log(f"Failed to copy: {chosen} -> {target}")
            return False
        else:
            msg = f"{count + 1}: {chosen} -> {target}"
            self.logger.log_message(msg)
            self.observer.on_log(msg)
            return True

    def _create_dest_folder(self) -> Path:
        """Create the destination folder based on configuration."""
        if not self.config.folders_model.create:
            return self.config.dest

        dest = self.config.dest
        name = self.config.folders_model.name
        target = dest / name

        x = 2
        while target.exists():
            target = dest / f"{name}_{x}"
            x += 1

        target.mkdir(parents=False)
        return target

    def _prepare_folder_targets(self) -> list[int]:
        """Prepare target file counts for each folder."""
        folder_count = self.config.folders_model.count
        self.observer.on_progress_total(folder_count)

        targets = [self.config.count_model.count] * folder_count

        if self.config.count_model.is_rand_count:
            for i in range(folder_count):
                targets[i] = self.rng.randint(
                    self.config.count_model.count_min_rand,
                    self.config.count_model.count_max_rand,
                )

        return targets

    def _handle_invalid(self, path: Path) -> None:
        """Handle logging of invalid files."""
        if self.config.execution_model.log_invalid:
            self.observer.on_log(f"Invalid: {path}")
        trash_path(path, condition=self.config.trash_model.invalid_file)

    def _is_stall_timeout(self) -> bool:
        """Check if the process has timed out based on stall time."""
        return (perf_counter() - self.state.start_time) > self.config.execution_model.stall_time_limit

    def _is_stop_condition(self) -> bool:
        """Check if the process should stop based on conditions."""
        return self.stop_requested or self.quota.all_locked() or self._is_stall_timeout()

    def _get_status_header(self, count: int, target: int) -> str:
        """Generate a status header for logging."""
        timed_out = self._is_stall_timeout()
        all_searched = self.quota.all_locked()

        copied_str = f"{count}/{target} files copied"

        if count == target:
            return f"SUCCESS: {copied_str}"

        if self.stop_requested:
            return f"STOPPED: {copied_str}"

        if count == 0 and self.config.folders_model.create and (timed_out or all_searched):
            reason = "timed out" if timed_out else "all files searched"
            return f"NO FILES FOUND: Reason - {reason} | {copied_str} | folder deleted"

        if all_searched:
            return f"ALL FILES SEARCHED: {copied_str}"

        if timed_out:
            return f"TIMED OUT: {copied_str}"

        return "FINISHED: Unknown reason"

    def _finalize_folder(self, dest: Path, count: int, target: int) -> None:
        """Create and write log at the end of folder."""
        runtime = round(perf_counter() - self.state.start_currdir, 2)

        status = self._get_status_header(count, target)
        report = self.logger.generate_report(dest, status, runtime)
        self.observer.on_log(report)
        self.logger.save(report)

        if count == 0 and self.config.folders_model.create:
            with contextlib.suppress(OSError):
                shutil.rmtree(dest)
