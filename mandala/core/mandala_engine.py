"""Mandala Engine Module."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from random import Random
from time import perf_counter
from typing import TYPE_CHECKING

import send2trash
from PySide6.QtCore import QObject, Signal

if TYPE_CHECKING:
    from .file_validator import FileValidator
    from .mandala_config import MandalaConfig
    from .mandala_logger import MandalaLogger
    from .mandala_state import MandalaState


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
    stop_requested: bool = False
    signals: MandalaEngineSignals = field(default_factory=MandalaEngineSignals)
    rng: Random = field(init=False)

    def __post_init__(self) -> None:
        """Initialize the file validator after the engine is created."""
        self.rng = Random(x=Random().random())

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

        top_mark = Path()
        curr_dest = self.create_dest_folder()
        self.logger.setup_for_folder(curr_dest)

        main_path = self.config.root

        # File Count
        num_files = self.get_file_count_for_folder()

        # self.ui_sect_exec.progbar_main.setRange(0, num_files)

        for index in range(num_files):
            if self.stop_requested:
                break

            if self.state.touched_folders[root_abs] and self.is_stall_timeout():
                break

            main_path = self.process_file(main_path, top_mark, index, curr_dest)

        self.finalize_folder(curr_dest)

    def process_file(self, main_path: Path, top_mark: Path, index: int, curr_dest: Path) -> Path:
        """Process a single file for copying."""
        while not (self.state.touched_folders[self.config.root_absolute] or self.is_stall_timeout()):
            if self.stop_requested:
                return main_path

            main_path_absolute = main_path.resolve()
            # Try to get main path
            try:
                if not self.state.path_cache.setdefault(main_path_absolute, []):
                    self.state.path_cache[main_path_absolute] = list(main_path.iterdir())
            except PermissionError:
                self.state.touched_folders[main_path_absolute] = True
                main_path = self.config.root
                continue

            # If folder is empty
            if len(self.state.path_cache[main_path_absolute]) == 0:
                self.state.touched_folders[main_path_absolute] = True

                if self.config.trash_empty_folders:
                    send2trash.send2trash(str(main_path_absolute))

                main_path = self.config.root
                continue

            # If the folder is not empty
            # Chooses random path and stores absolute path
            _path = Path(self.rng.choice(self.state.path_cache[main_path_absolute]))
            _abs_path = _path.resolve()

            # If touched, try again:
            if self.state.touched_files[_abs_path] or self.state.touched_folders[_abs_path]:
                self.state.touch_folder_if_all_files_touched(main_path_absolute)
                main_path = self.config.root
            elif _path.is_dir():
                main_path, top_mark = self.enter_directory(_path, _abs_path, main_path, top_mark)
            elif _path.is_file():
                # Touch the file and get size
                self.state.touched_files[_abs_path] = True
                _pathsize = _path.stat().st_size
                _rel_path = Path(os.path.relpath(_path, self.config.root))
                # If file is valid
                if self.validator.is_valid(_path, _pathsize) and self.copy_file(index, _path, curr_dest, _pathsize):
                    self.log_success(_rel_path, index)

                    self.state.bytes_in_current_folder += _pathsize

                    self.state.count += 1
                    self.signals.count.emit(self.state.count)

                    self.state.start_stall_time = perf_counter()
                    self.signals.time.emit()

                    if self.config.trash_source_files:
                        send2trash.send2trash(str(_abs_path))

                    self.handle_weights(top_mark, main_path_absolute)
                    main_path = self.config.root
                    break

                # If file is invalid
                self.log_invalid(_rel_path)

                main_path = self.config.root

        return main_path

    def get_file_count_for_folder(self) -> int:
        """Get the number of files to process for the current folder."""
        if self.config.is_rand_file_count:
            return self.rng.randint(self.config.num_files_rand_min, self.config.num_files_rand_max)
        return self.config.num_files

    def create_dest_folder(self) -> Path:
        """Create the destination folder based on configuration."""
        if not self.config.create_folders:
            return self.config.dest

        dest = self.config.dest
        name = self.config.folder_name
        final_dest = dest / name
        x = 2
        while True:
            if not final_dest.exists():
                final_dest.mkdir()
                return final_dest

            final_dest = dest / f"{name} {x}"
            x += 1

    def log_success(self, random_path: Path, curr_file: int) -> None:
        """Handle logging of valid files."""
        msg = f"{curr_file + 1}: {random_path}"
        self.logger.write_log(msg)
        self.signals.log.emit(msg)

    def log_invalid(self, path: Path) -> None:
        """Handle logging of invalid files."""
        if self.config.log_invalid:
            self.signals.log.emit(f"Invalid: {path}")

        if self.config.trash_invalid_files:
            send2trash.send2trash(path.resolve())

    def handle_weights(self, top_mark: Path, bottom_mark: Path) -> None:
        """Handle weight assignments for folders."""
        weight_top = self.config.weight_top
        weight_bottom = self.config.weight_bottom
        weighted_counts = self.state.weighted_counts
        touched_folders = self.state.touched_folders
        touched_by_weight = self.state.touched_by_weight

        if weight_top > 0:
            weighted_counts[top_mark] += 1
            if weighted_counts[top_mark] == weight_top:
                touched_folders[top_mark] = True
                touched_by_weight[top_mark] = True

        if weight_bottom > 0:
            weighted_counts[bottom_mark] += 1
            if weighted_counts[bottom_mark] == weight_bottom:
                touched_folders[bottom_mark] = True
                touched_by_weight[bottom_mark] = True

    def is_stall_timeout(self) -> bool:
        """Check if the process has timed out based on stall time."""
        return (perf_counter() - self.state.start_stall_time) > self.config.stall_time_limit

    def enter_directory(self, path: Path, abs_path: Path, main_path: Path, top_mark: Path) -> tuple[Path, Path]:
        """Handle the case when the random path is a directory."""
        try:
            os.chdir(path)
            main_path = Path.cwd()
            if self.config.weight_top > 0 and abs_path.parent == self.config.root:
                top_mark = abs_path
        except PermissionError:
            self.state.touched_folders[abs_path] = True
            main_path = self.config.root
        return main_path, top_mark

    def copy_file(self, index: int, src: Path, dest: Path, size: int) -> bool | None:
        """Copy files to the target destination with appropriate naming."""
        try:
            src_abs = src.resolve()
            src_name = src.name

            _target = dest / src_name

            if self.config.index_files:
                _target = dest / f"{index + 1}.{src_name}"
            elif self.config.rename_files:
                rn = self.config.rename_name
                _target = dest / f"{rn} {index + 1}{src.suffix}"

                x = 1
                while _target.exists():
                    x += 1
                    _target = dest / f"{rn} {index + x}{src.suffix}"
            else:
                x = 2
                while _target.exists():
                    if size == _target.stat().st_size:
                        return False

                    _target = dest / f"{src.stem} ({x}){src.suffix}"
                    x += 1
            shutil.copy(src_abs, _target)
        except PermissionError:
            return False
        else:
            return True

    def finalize_folder(self, curr_dest: Path) -> None:
        """Create and write log at the end of folder."""
        runtime = round(perf_counter() - self.state.start_folder_time, 2)
        timed_out = self.is_stall_timeout()
        all_searched = self.state.touched_folders[self.config.root_absolute]
        num_files = self.config.num_files
        found = self.state.count
        create_folders = self.config.create_folders

        if found == num_files:
            status = f"SUCCESS: {found}/{num_files} files copied"
        elif self.stop_requested:
            status = f"STOPPED: {found}/{num_files} files copied"
        elif found == 0 and create_folders and (timed_out or all_searched):
            reason = "timed out" if timed_out else "all files searched"
            status = f"NO FILES FOUND: {reason} | folder deleted"
        elif all_searched:
            status = f"ALL FILES SEARCHED: {found}/{num_files} files copied"
        elif timed_out:
            status = f"TIMED OUT: {found}/{num_files} files copied"
        else:
            status = "FINISHED"

        report = self.logger.generate_report(curr_dest, status, runtime)
        self.signals.log.emit(report)
        self.logger.close()
        self.logger.finalize_log(report)

        if found == 0:
            if create_folders:
                shutil.rmtree(curr_dest)
            else:
                self.logger.cleanup_empty()

    def request_stop(self) -> None:
        """Request to stop the engine."""
        self.stop_requested = True
