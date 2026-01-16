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

    from ..config.config import MandalaConfig
    from ..utils.interfaces import MandalaObserver
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
    rng: Random
    quota: DiversityQuota
    walker: RandomFSWalker
    observer: MandalaObserver = field(init=False)
    _request_stop: bool = False

    def set_observer(self, observer: MandalaObserver) -> None:
        """Set the observer for the engine."""
        self.observer = observer

    def request_stop(self) -> None:
        """Request to stop the engine."""
        self._request_stop = True

    def start(self) -> None:
        """Run the main file copying process."""
        clear_history = not self.config.folder.unique

        for target in self._generate_folder_target_counts():
            if self._request_stop:
                break

            self.state.reset_for_folder()
            self.quota.prepare_for_batch(clear_history=clear_history)
            self.process_folder(target)

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
                self.state.update_success(size)
                self.quota.register_success(path)
                self.observer.on_count(count)
                self.observer.on_time()
                trash_path(path, condition=self.config.trash.source_file)
            else:
                if self.config.execution.log_invalid:
                    self._report(msg=f"INVALID: {path.relative_to(self.config.root)}")
                trash_path(path, condition=self.config.trash.invalid_file)

        self.observer.on_count_total()
        self._finalize_folder(dest_dir, count, target)

    def _try_copy(self, chosen: Path, dest: Path, count: int) -> bool:
        """Attempt to copy a file and return success status."""
        target = calc_dest_file_path(self.config.filename, chosen, dest, count)
        if target is None:
            return False

        chosen_rel = chosen.relative_to(self.config.root)
        target_rel = target.relative_to(self.config.dest)
        copy_path_str = f"{chosen_rel} -> {target_rel}"

        if self.config.execution.dry_run:
            self._report(msg=f"DRY RUN: {count + 1}: {copy_path_str}")
            return True

        try:
            shutil.copy2(chosen, target)
        except (PermissionError, OSError):
            self._report(msg=f"FAILED COPY: {copy_path_str}")
            return False
        else:
            self._report(msg=f"{count + 1}: {copy_path_str}")
            return True

    def _report(self, msg: str) -> None:
        """Report and log a message."""
        self.reporter.record_message(msg)
        self.observer.on_log(msg)

    def _generate_folder_target_counts(self) -> Iterator[int]:
        """Prepare target file counts for each folder."""
        folder_count = self.config.folder.count
        file_count_model = self.config.filecount
        self.observer.on_progress_total(folder_count)
        for _ in range(folder_count):
            if file_count_model.is_rand_count:
                yield self.rng.randint(
                    file_count_model.count_min_rand,
                    file_count_model.count_max_rand,
                )
            else:
                yield file_count_model.count

    def _is_stall_timeout(self) -> bool:
        """Check if the process has timed out based on stall time."""
        return (perf_counter() - self.state.start_time_file) > self.config.progress.stall_time_limit

    def _is_stop_condition(self) -> bool:
        """Check if the process should stop based on conditions."""
        return self._request_stop or self.quota.all_locked() or self._is_stall_timeout()

    def _finalize_folder(self, dest: Path, count: int, target: int) -> None:
        """Create and write log at the end of folder."""
        runtime = round(perf_counter() - self.state.start_time_currdir, 2)
        copied = f"{count}/{target} files copied"
        create_folders = self.config.folder.create
        none_found = count == 0 and create_folders
        prefix = get_status_header(
            success=(count == target),
            stopped=self._request_stop,
            none_found=none_found,
            timeout=self._is_stall_timeout(),
            all_searched=self.quota.all_locked(),
        )
        status = f"{prefix}: {copied}"

        report = self.reporter.generate_report(dest, status, runtime, self.state.bytes_in_currdir)
        self._report(report)
        self.reporter.save()

        if none_found:
            with contextlib.suppress(OSError):
                shutil.rmtree(dest)
