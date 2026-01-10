"""Logger for Mandala process."""

from __future__ import annotations

import contextlib
import shutil
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, TextIO

from ..utilities.utils import convert_byte_to_size

if TYPE_CHECKING:
    from .mandala_config import MandalaConfig
    from .mandala_state import MandalaState


@dataclass(slots=True)
class MandalaLogger:
    """Logger class for Mandala."""

    config: MandalaConfig
    state: MandalaState

    log: TextIO = field(init=False)
    log_temp: TextIO = field(init=False)
    log_path: Path = field(init=False)
    log_temp_path: Path = field(init=False)

    def setup_for_folder(self, dest_folder: Path) -> None:
        """Initialize log files for a specific destination folder."""
        # Determine log path based on folder strategy
        self.log_path = dest_folder / f"!{dest_folder.name}_log.txt"

        if self.config.create_folders:
            pass

        self.state.is_append_log = self.log_path.exists()

        # Open main log (append mode)
        self.log = self.log_path.open("a", encoding="utf-8")

        # Open temp log (for current run details)
        self.log_temp_path = Path(self.log_path.stem + ".tmp.txt")
        self.log_temp = self.log_temp_path.open("a", encoding="utf-8")

    def write_log(self, message: str) -> None:
        """Write to the appropriate log stream."""
        if self.state.is_append_log and self.log_temp:
            self.log_temp.write(f"{message}\n")
        elif self.log:
            self.log.write(f"{message}\n")

    def close(self) -> None:
        """Close file handles."""
        if self.log_temp:
            self.log_temp.close()
        if self.log:
            self.log.close()

    def generate_report(self, dest: Path, status: str, runtime: float) -> str:
        """Generate the header report string."""
        _extensions = self.config.extensions
        _keywords = self.config.keywords
        ext_str = ", ".join([f".{e}" for e in _extensions]) if _extensions else "All"
        kw_str = ", ".join([f'"{k}"' for k in _keywords]) if _keywords else "All"

        return (
            "------------------------------------------------------------------------\n"
            f"{status}\n"
            "------------------------------------------------------------------------\n"
            f"Date:             {datetime.now(tz=UTC).strftime('%B %d, %Y')}\n"
            f"Time:             {datetime.now(tz=UTC).strftime('%I:%M:%S%p')}\n"
            f"Start:            {self.config.root}\n"
            f"Destination:      {dest}\n"
            f"Extensions:       {ext_str}\n"
            f"Keywords:         {kw_str}\n"
            f"Total size:       {convert_byte_to_size(self.state.bytes_in_current_folder)}\n"
            f"Total runtime:    {runtime}s\n"
            "------------------------------------------------------------------------"
        )

    def finalize_log(self, report: str) -> None:
        """Prepend status report to the log file and clean up temp files."""
        # Re-open files for reading/writing logic
        log_path = self.log_path
        temp_path = self.log_temp_path

        if self.state.is_append_log:
            # Append temp content (current run) to main log, with report in between?
            # Based on original logic:
            with temp_path.open(encoding="utf-8") as content, log_path.open("a", encoding="utf-8") as out:
                out.write(report + "\n")
                shutil.copyfileobj(content, out)
            temp_path.unlink()
        else:
            # New log: Write report first, then copy temp content (list of files)
            with log_path.open(encoding="utf-8") as existing, temp_path.open("w", encoding="utf-8") as out:
                out.write(report + "\n")
                shutil.copyfileobj(existing, out)
            shutil.move(temp_path, log_path)

    def cleanup_empty(self) -> None:
        """Delete log if no files were found."""
        self.close()
        if not (self.config.create_folders or self.state.is_append_log) and (self.log_path and self.log_path.exists()):
            with contextlib.suppress(OSError):
                self.log_path.unlink()
