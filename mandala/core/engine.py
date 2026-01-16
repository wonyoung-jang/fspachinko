"""Mandala Engine Module."""

from __future__ import annotations

import contextlib
import shutil
from dataclasses import dataclass, field
from time import perf_counter
from typing import TYPE_CHECKING

from ..utils.helpers import calc_dest_file_path, create_dest_folder, get_status_header, trash_path

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path
    from random import Random

    from ..config.config import MandalaConfig
    from ..utils.interfaces import MandalaObserver
    from .quota import DiversityQuota
    from .reporter import ReportWriter
    from .validator import FileValidator
    from .walker import RandomFSWalker


@dataclass(slots=True)
class MandalaState:
    """Dataclass for Mandala state."""

    bytes_in_currdir: int = 0
    start_time_currdir: float = 0.0
    start_time_file: float = 0.0

    def reset_for_folder(self) -> None:
        """Reset state variables for a new folder."""
        self.bytes_in_currdir = 0
        _start = perf_counter()
        self.start_time_currdir = _start
        self.start_time_file = _start

    def update_success(self, size: int) -> None:
        """Update state on successful operation."""
        self.bytes_in_currdir += size
        self.start_time_file = perf_counter()


@dataclass(slots=True)
class MandalaEngine:
    """Core engine class for Mandala."""

    config: MandalaConfig
    validator: FileValidator
    reporter: ReportWriter
    rng: Random
    quota: DiversityQuota
    walker: RandomFSWalker
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

            if self.validator.is_valid(path, size) and self._try_copy(path, dest, copied):
                copied += 1
                self._state.update_success(size)
                self.quota.register_success(path)
                self.observer.on_count(copied)
                self.observer.on_time()
                trash_path(path, condition=self.config.trash.source_file)
            else:
                if self.config.execution.log_invalid:
                    self._report(msg=f"INVALID: {path.relative_to(self.config.root)}")
                trash_path(path, condition=self.config.trash.invalid_file)

        return copied

    def _complete_folder(self, dest: Path, copied: int, target: int) -> None:
        """Post-process actions after folder processing."""
        self.observer.on_count_total()
        self._finalize_folder(dest, copied, target)

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

    def _generate_target_and_dest(self) -> Iterator[tuple[int, Path]]:
        """Prepare target file counts for each folder."""
        folder_count = self.config.folder.count
        filecount_model = self.config.filecount
        self.observer.on_progress_total(folder_count)

        fcount = filecount_model.count
        is_rand = filecount_model.is_rand_count
        rmin = filecount_model.count_min_rand
        rmax = filecount_model.count_max_rand
        counts = [self.rng.randint(rmin, rmax) if is_rand else fcount for _ in range(folder_count)]
        folders = [create_dest_folder(self.config.folder, self.config.dest) for _ in range(folder_count)]

        yield from zip(counts, folders, strict=True)

    def _is_stall_timeout(self) -> bool:
        """Check if the process has timed out based on stall time."""
        return (perf_counter() - self._state.start_time_file) > self.config.progress.stall_time_limit

    def _is_stop_condition(self) -> bool:
        """Check if the process should stop based on conditions."""
        return self._request_stop or self.quota.all_locked() or self._is_stall_timeout()

    def _finalize_folder(self, dest: Path, count: int, target: int) -> None:
        """Create and write log at the end of folder."""
        runtime = round(perf_counter() - self._state.start_time_currdir, 2)
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

        report = self.reporter.generate_report(dest, status, runtime, self._state.bytes_in_currdir)
        self._report(report)
        self.reporter.save()

        if none_found:
            with contextlib.suppress(OSError):
                shutil.rmtree(dest)
