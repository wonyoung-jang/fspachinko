"""Mandala Engine Module."""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from time import perf_counter
from typing import TYPE_CHECKING

import send2trash
from PySide6.QtCore import QObject, Signal

if TYPE_CHECKING:
    from pathlib import Path

    from mandala.core.config_validator import FileValidator
    from mandala.core.mandala_config import MandalaConfig
    from mandala.core.mandala_logger import MandalaLogger
    from mandala.core.mandala_state import MandalaState


class MandalaEngineSignals(QObject):
    """Signals for Mandala Engine."""

    finished = Signal()
    log = Signal(str)
    progress = Signal()
    stall_reset = Signal()


@dataclass(slots=True)
class MandalaEngine:
    """Core engine class for Mandala."""

    config: MandalaConfig
    state: MandalaState
    validator: FileValidator
    logger: MandalaLogger
    signals: MandalaEngineSignals = field(default_factory=MandalaEngineSignals)
    stop_requested: bool = False

    def __post_init__(self) -> None:
        """Initialize the file validator after the engine is created."""

    def start(self) -> None:
        """Run the main file copying process."""
        for _ in range(self.config.num_folders):
            if self.stop_requested:
                break

            self.process_folder()

        self.stop()

    def process_folder(self) -> None:
        """Process a single folder based on the current configuration."""

    def stop(self) -> None:
        """Stop the Mandala process."""
        self.stop_requested = True

    def create_dest_folder(self) -> Path:
        """Create the destination folder based on configuration."""
        dest = self.config.dest
        if not self.config.create_folders:
            return dest

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

    def is_timed_out(self) -> bool:
        """Check if the process has timed out based on stall time."""
        return (perf_counter() - self.state.start_stall_time) > self.config.stall_time_limit

    def finalize_folder(self, curr_dest: Path) -> None:
        """Create and write log at the end of folder."""
        runtime = round(perf_counter() - self.state.start_folder_time, 2)
        timed_out = self.is_timed_out()
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
