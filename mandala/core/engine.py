"""Mandala Engine Module."""

from __future__ import annotations

import contextlib
import filecmp
import shutil
from dataclasses import dataclass, field
from time import perf_counter
from typing import TYPE_CHECKING

from .helpers import trash_path

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
        clear_history = not self.config.unique_folders

        for _ in range(self.config.num_folders):
            if self.stop_requested:
                break

            self.state.reset_for_folder()
            self.quota.prepare_for_batch(clear_history=clear_history)
            self.process_folder()

        self.observer.on_finished()

    def process_folder(self) -> None:
        """Process a single folder for file copying."""
        dest_dir = self._create_dest_folder()
        self.logger.setup_for_folder(dest_dir)

        index = 0
        target = self._get_target_count()

        for candidate in self.walker.generate_candidates():
            if index >= target:
                break

            if self._is_stop_condition():
                break

            if candidate is None:
                break

            if not self.validator.is_valid(candidate):
                self._handle_invalid(candidate.path)
                continue

            if self._try_copy(candidate.path, dest_dir, index):
                index += 1
                self.quota.register_success(candidate.path)
                self.state.update_success(candidate.size)
                self.observer.on_count(index)
                self.observer.on_time()
                trash_path(candidate.path, condition=self.config.trash_source_files)
            else:
                self._handle_invalid(candidate.path)

        self._finalize_folder(dest_dir)

    def _try_copy(self, chosen: Path, dest: Path, index: int) -> bool:
        """Attempt to copy a file and return success status."""
        target = self._calc_dest_file_path(chosen, dest, index)
        if target is None:
            return False

        try:
            shutil.copy(chosen, target)
        except (PermissionError, OSError):
            return False

        # Success
        msg = f"{index + 1}: {chosen} -> {target}"
        self.logger.write_log(msg)
        self.observer.on_log(msg)
        return True

    def _get_target_count(self) -> int:
        """Get the number of files to process for the current folder."""
        if self.config.is_rand_file_count:
            return self.rng.randint(self.config.num_files_rand_min, self.config.num_files_rand_max)
        return self.config.num_files

    def _create_dest_folder(self) -> Path:
        """Create the destination folder based on configuration."""
        if not self.config.create_folders:
            return self.config.dest

        dest = self.config.dest
        name = self.config.folder_name
        target = dest / name

        x = 2
        while target.exists():
            target = dest / f"{name}_{x}"
            x += 1

        target.mkdir(parents=False)
        return target

    def _calc_dest_file_path(self, chosen: Path, dest: Path, index: int) -> Path | None:
        """Calculate the destination file path based on naming conventions."""
        ext = chosen.suffix
        stem = chosen.stem

        is_index = self.config.index_files
        is_rename = self.config.rename_files
        new_name = self.config.rename_name

        if is_index:
            name = f"{index + 1}_{stem}{ext}"
        elif is_rename:
            name = f"{new_name}_{index + 1}{ext}"
        else:
            name = chosen.name

        target = dest / name

        if target.exists() and filecmp.cmp(chosen, target) and not (is_rename or is_index):
            return None

        x = 2
        base_stem = target.stem
        while target.exists():
            target = dest / f"{base_stem} ({x}){ext}"
            x += 1

        return target

    def _handle_invalid(self, path: Path) -> None:
        """Handle logging of invalid files."""
        if self.config.log_invalid:
            self.observer.on_log(f"Invalid: {path}")
        trash_path(path, condition=self.config.trash_invalid_files)

    def _is_stall_timeout(self) -> bool:
        """Check if the process has timed out based on stall time."""
        return (perf_counter() - self.state.start_time) > self.config.stall_time_limit

    def _is_stop_condition(self) -> bool:
        """Check if the process should stop based on conditions."""
        return self.stop_requested or self.quota.all_locked() or self._is_stall_timeout()

    def _finalize_folder(self, dest: Path) -> None:
        """Create and write log at the end of folder."""
        runtime = round(perf_counter() - self.state.start_currdir, 2)

        timed_out = self._is_stall_timeout()
        all_searched = self.quota.all_locked()

        count = self.state.count
        num_files = self.config.num_files
        create_folders = self.config.create_folders

        if count == num_files:
            status = f"SUCCESS: {count}/{num_files} files copied"
        elif self.stop_requested:
            status = f"STOPPED: {count}/{num_files} files copied"
        elif count == 0 and create_folders and (timed_out or all_searched):
            reason = "timed out" if timed_out else "all files searched"
            status = f"NO FILES FOUND: {reason} | folder deleted"
        elif all_searched:
            status = f"ALL FILES SEARCHED: {count}/{num_files} files copied"
        elif timed_out:
            status = f"TIMED OUT: {count}/{num_files} files copied"
        else:
            status = "FINISHED"

        report = self.logger.generate_report(dest, status, runtime)
        self.observer.on_log(report)
        self.logger.close()
        self.logger.finalize_log(report)

        if count == 0 and create_folders:
            with contextlib.suppress(OSError):
                shutil.rmtree(dest)
            self.logger.cleanup_empty()
