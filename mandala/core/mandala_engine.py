"""Mandala Engine Module."""

from __future__ import annotations

import contextlib
import shutil
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import TYPE_CHECKING

import send2trash
from PySide6.QtCore import QObject, Signal

if TYPE_CHECKING:
    from random import Random

    from .file_validator import FileValidator
    from .mandala_config import MandalaConfig
    from .mandala_logger import MandalaLogger
    from .mandala_state import MandalaState


def trash_path(path: Path, *, condition: bool) -> None:
    """Trash a path if the condition is met."""
    if condition:
        with contextlib.suppress(Exception):
            send2trash.send2trash(path)


class MandalaEngineSignals(QObject):
    """Signals for Mandala Engine."""

    finished = Signal()
    log = Signal(str)
    time = Signal()
    count = Signal(int)


@dataclass(slots=True)
class MandalaEngine:
    """Core engine class for Mandala."""

    config: MandalaConfig
    state: MandalaState
    validator: FileValidator
    logger: MandalaLogger
    stop_requested: bool
    signals: MandalaEngineSignals
    rng: Random

    def start(self) -> None:
        """Run the main file copying process."""
        for _ in range(self.config.num_folders):
            if self.stop_requested:
                break

            self.process_folder()

        self.signals.finished.emit()

    def process_folder(self) -> None:
        """Process a single folder for file copying."""
        root_abs = self.config.root_absolute
        self.state.reset_for_folder(root_abs, unique_folders=self.config.unique_folders)

        top = Path()
        dest = self._create_dest_folder()
        self.logger.setup_for_folder(dest)

        main = self.config.root
        for index in range(self._get_file_count_for_folder()):
            if self.stop_requested or self._is_stop_condition():
                break

            main = self.process_file(main, top, index, dest)

        self._finalize_folder(dest)

    def process_file(self, main: Path, top: Path, index: int, dest: Path) -> Path:
        """Process a single file for copying."""
        root = self.config.root
        start = main

        while not (self.state.touched_folders[self.config.root_absolute] or self._is_stall_timeout()):
            if self.stop_requested:
                break

            start_abs = start.resolve()

            choices = self._select_random_path(start, start_abs)
            if choices is None:
                start = root
                continue

            chosen, chosen_abs = choices

            if chosen.is_dir():
                start, top = self._enter_directory(chosen, chosen_abs, start, top)
                continue

            if chosen.is_file():
                self.state.touched_files[chosen_abs] = True

                if self._attempt_copy_file(chosen, dest, index, top, start):
                    return root

                start = root
                continue

        return start

    def _select_random_path(self, start: Path, start_abs: Path) -> tuple[Path, ...] | None:
        """Select a random path from the given start directory."""
        try:
            if not self.state.path_cache.setdefault(start_abs, []):
                self.state.path_cache[start_abs] = list(start.glob("*"))
        except PermissionError:
            self.state.touched_folders[start_abs] = True
            return None

        # If folder is empty
        if not (children := self.state.path_cache[start_abs]):
            self.state.touched_folders[start_abs] = True

            # Trash empty folder if configured
            trash_path(start_abs, condition=self.config.trash_empty_folders)
            return None

        # If the folder is not empty
        # Chooses random path and stores absolute path
        chosen = self.rng.choice(children)
        chosen_abs = chosen.resolve()

        # If touched, try again:
        if self.state.is_touched(chosen_abs):
            self.state.touch_folder_if_all_files_touched(start_abs)
            return None

        return chosen, chosen_abs

    def _attempt_copy_file(self, chosen: Path, dest: Path, index: int, top: Path, start: Path) -> bool:
        """Attempt to copy a file and return success status."""
        chosen_abs = chosen.resolve()
        chosen_rel = chosen.relative_to(self.config.root)

        size = chosen.stat().st_size

        if not self.validator.is_valid(chosen, size):
            self._handle_invalid(chosen_rel, chosen_abs, to_trash=self.config.trash_invalid_files)
            return False

        target_path = self._calc_dest_file_path(chosen, dest, index, size)
        if target_path is None:
            self._handle_invalid(chosen_rel, chosen_abs, to_trash=self.config.trash_invalid_files)
            return False

        try:
            shutil.copy(chosen_abs, target_path)
        except PermissionError:
            self._handle_invalid(chosen_rel, chosen_abs, to_trash=self.config.trash_invalid_files)
            return False

        # Success
        self._log_success(chosen_rel, index)
        self.state.update_success(size)
        self.signals.count.emit(self.state.count)
        self.signals.time.emit()
        trash_path(chosen_abs, condition=self.config.trash_source_files)
        self._handle_weights(top, start.resolve())
        return True

    def _handle_invalid(self, chosen_rel: Path, chosen_abs: Path, *, to_trash: bool) -> None:
        """Reset state after encountering an invalid file."""
        self._log_invalid(chosen_rel)
        trash_path(chosen_abs, condition=to_trash)

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
        all_searched = self.state.touched_folders[self.config.root_absolute]
        timed_out = self._is_stall_timeout()
        return all_searched and timed_out

    def _is_stall_timeout(self) -> bool:
        """Check if the process has timed out based on stall time."""
        return (perf_counter() - self.state.start_stall_time) > self.config.stall_time_limit

    def _finalize_folder(self, dest: Path) -> None:
        """Create and write log at the end of folder."""
        runtime = round(perf_counter() - self.state.start_folder_time, 2)
        timed_out = self._is_stall_timeout()
        all_searched = self.state.touched_folders[self.config.root_absolute]
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
        self.signals.log.emit(report)
        self.logger.close()
        self.logger.finalize_log(report)

        if count == 0:
            if create_folders:
                shutil.rmtree(dest)
            else:
                self.logger.cleanup_empty()

    def _enter_directory(self, chosen: Path, chosen_abs: Path, start: Path, top: Path) -> tuple[Path, Path]:
        """Handle the case when the random path is a directory."""
        start = chosen
        if self.config.weight_top > 0 and chosen_abs.parent == self.config.root:
            top = chosen_abs
        return start, top

    def _calc_dest_file_path(self, chosen: Path, dest: Path, index: int, size: int) -> Path | None:
        """Calculate the destination file path based on naming conventions."""
        target = dest / chosen.name

        if self.config.index_files:
            target = dest / f"{index + 1}.{chosen.name}"
        elif self.config.rename_files:
            rn = self.config.rename_name
            target = dest / f"{rn} {index + 1}{chosen.suffix}"

            x = 1
            while target.exists():
                x += 1
                target = dest / f"{rn} {index + x}{chosen.suffix}"
        else:
            x = 2
            while target.exists():
                if size == target.stat().st_size:
                    return None

                target = dest / f"{chosen.stem} ({x}){chosen.suffix}"
                x += 1

        return target

    def _log_success(self, random_path: Path, curr_file: int) -> None:
        """Handle logging of valid files."""
        msg = f"{curr_file + 1}: {random_path}"
        self.logger.write_log(msg)
        self.signals.log.emit(msg)

    def _handle_weights(self, top: Path, bottom: Path) -> None:
        """Handle weight assignments for folders."""
        self.state.handle_weight(top, self.config.weight_top)
        self.state.handle_weight(bottom, self.config.weight_bottom)

    def _log_invalid(self, path: Path) -> None:
        """Handle logging of invalid files."""
        if self.config.log_invalid:
            self.signals.log.emit(f"Invalid: {path}")

    def request_stop(self) -> None:
        """Request to stop the engine."""
        self.stop_requested = True
