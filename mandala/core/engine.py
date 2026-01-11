"""Mandala Engine Module."""

from __future__ import annotations

import contextlib
import shutil
from dataclasses import dataclass, field
from time import perf_counter
from typing import TYPE_CHECKING

import send2trash

if TYPE_CHECKING:
    from pathlib import Path
    from random import Random

    from .config import MandalaConfig
    from .interfaces import MandalaObserver
    from .logger import MandalaLogger
    from .quota import DiversityQuota
    from .state import MandalaState
    from .validator import FileValidator


def trash_path(path: Path, *, condition: bool) -> None:
    """Trash a path if the condition is met."""
    if condition:
        with contextlib.suppress(Exception):
            send2trash.send2trash(path)


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
    observer: MandalaObserver = field(init=False)

    def set_observer(self, observer: MandalaObserver) -> None:
        """Set the observer for the engine."""
        self.observer = observer

    def start(self) -> None:
        """Run the main file copying process."""
        for _ in range(self.config.num_folders):
            if self.stop_requested:
                break

            self.process_folder()

        self.observer.on_finished()

    def process_folder(self) -> None:
        """Process a single folder for file copying."""
        self.state.reset_for_folder()
        self.quota.prepare_for_batch(clear_history=not self.config.unique_folders)

        dest_dir = self._create_dest_folder()
        self.logger.setup_for_folder(dest_dir)

        curr_rootdir = self.config.root
        input_leafdir = self.config.root

        for index in range(self._get_file_count_for_folder()):
            if self._is_stop_condition():
                break

            self.process_file(input_leafdir, curr_rootdir, index, dest_dir)

        self._finalize_folder(dest_dir)

    def process_file(self, input_leafdir: Path, curr_rootdir: Path, index: int, dest_dir: Path) -> None:
        """Process a single file for copying."""
        base_rootdir = self.config.root
        curr_leafdir = input_leafdir

        while True:
            if self._is_stop_condition():
                return

            chosen_path = self._select_random_path(curr_leafdir)
            if chosen_path is None:
                self.quota.lock_folder(curr_leafdir)
                curr_leafdir = base_rootdir
                continue

            if chosen_path.is_dir():
                curr_leafdir, curr_rootdir = self._enter_folder(chosen_path, curr_rootdir)
                continue

            if chosen_path.is_file():
                self.quota.lock_file(chosen_path)

                chosen_new = self._attempt_copy_file(chosen_path, dest_dir, index)

                if not chosen_new:
                    self._log_invalid(chosen_path)
                    trash_path(chosen_path, condition=self.config.trash_invalid_files)
                    curr_leafdir = base_rootdir
                    continue

                self._log_success(chosen_path, chosen_new, index)
                self._do_success(chosen_new.stat().st_size)
                self._handle_locks(curr_rootdir, curr_leafdir)
                trash_path(chosen_path, condition=self.config.trash_source_files)
                return

    def _do_success(self, size: int) -> None:
        """Handle successful file copy operations."""
        self.state.update_success(size)
        self.observer.on_count(self.state.count)
        self.observer.on_time()

    def _select_random_path(self, curr_leafdir: Path) -> Path | None:
        """Select a random path from the given start directory."""
        try:
            curr_leafdir_content = list(curr_leafdir.glob("*"))
        except PermissionError:
            return None

        if not curr_leafdir_content:
            trash_path(curr_leafdir, condition=self.config.trash_empty_folders)
            return None

        self.rng.shuffle(curr_leafdir_content)
        available_content = (p for p in curr_leafdir_content if self.quota.is_available(p))

        if (chosen_path := next(available_content, None)) is None:
            return None

        return chosen_path

    def _attempt_copy_file(self, chosen: Path, dest: Path, index: int) -> Path | None:
        """Attempt to copy a file and return success status."""
        if not self.validator.is_valid(chosen):
            return None

        target = self._calc_dest_file_path(chosen, dest, index)

        try:
            shutil.copy(chosen, target)
        except PermissionError:
            return None

        return target

    def _create_dest_folder(self) -> Path:
        """Create the destination folder based on configuration."""
        dest = self.config.dest
        if not self.config.create_folders:
            return dest

        name = self.config.folder_name
        final_dest = dest / name
        x = 2
        while final_dest.exists():
            final_dest = dest / f"{name}_{x}"
            x += 1

        final_dest.mkdir(parents=False, exist_ok=False)
        return final_dest

    def _get_file_count_for_folder(self) -> int:
        """Get the number of files to process for the current folder."""
        if self.config.is_rand_file_count:
            return self.rng.randint(self.config.num_files_rand_min, self.config.num_files_rand_max)
        return self.config.num_files

    def _is_stop_condition(self) -> bool:
        """Check if the process should stop based on conditions."""
        return self.stop_requested or self.quota.all_locked() or self._is_stall_timeout()

    def _is_stall_timeout(self) -> bool:
        """Check if the process has timed out based on stall time."""
        return (perf_counter() - self.state.start_stall_time) > self.config.stall_time_limit

    def _finalize_folder(self, dest: Path) -> None:
        """Create and write log at the end of folder."""
        runtime = round(perf_counter() - self.state.start_folder_time, 2)

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

        if count == 0:
            if create_folders:
                shutil.rmtree(dest)
            else:
                self.logger.cleanup_empty()

    def _enter_folder(self, chosen: Path, top: Path) -> tuple[Path, Path]:
        """Handle the case when the random path is a directory."""
        if self.config.weight_top > 0 and chosen.parent == self.config.root:
            top = chosen
        return chosen, top

    def _calc_dest_file_path(self, chosen: Path, dest: Path, index: int) -> Path:
        """Calculate the destination file path based on naming conventions."""
        if self.config.index_files:
            name = f"{index + 1}.{chosen.name}"
            return dest / name

        ext = chosen.suffix
        new_name = self.config.rename_name

        if self.config.rename_files:
            name = f"{new_name} {index + 1}{ext}"
            target = dest / name

            x = 1
            while target.exists():
                name = f"{new_name} {index + x}{ext}"
                target = dest / name
                x += 1

            return target

        target = dest / chosen.name
        stem = chosen.stem

        x = 2
        while target.exists():
            name = f"{stem} ({x}){ext}"
            target = dest / name
            x += 1

        return target

    def _handle_locks(self, curr_root: Path, curr_leaf: Path) -> None:
        """Handle lock assignments for folders."""
        self.quota.update_and_lock(curr_root, self.config.weight_top)
        self.quota.update_and_lock(curr_leaf, self.config.weight_bottom)

    def _log_success(self, chosen_file: Path, chosen_new: Path, index: int) -> None:
        """Handle logging of valid files."""
        msg = f"{index + 1}: {chosen_file} -> {chosen_new}"
        self.logger.write_log(msg)
        self.observer.on_log(msg)

    def _log_invalid(self, path: Path) -> None:
        """Handle logging of invalid files."""
        if self.config.log_invalid:
            self.observer.on_log(f"Invalid: {path}")

    def request_stop(self) -> None:
        """Request to stop the engine."""
        self.stop_requested = True
