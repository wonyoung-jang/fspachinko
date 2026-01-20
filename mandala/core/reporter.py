"""Reporter for Mandala process."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..utils.constants import BYTE_TO_GIGABYTE, BYTE_TO_MEGABYTE, BYTES_IN_GIGABYTE

if TYPE_CHECKING:
    from pathlib import Path

    from .timestamp import DateTimeSingleton


def convert_byte_to_size(bytes_in_curr_dir: int) -> str:
    """Convert bytes to MB or GB string."""
    if bytes_in_curr_dir < BYTES_IN_GIGABYTE - 1:
        return f"{round(bytes_in_curr_dir * BYTE_TO_MEGABYTE, 2)} MB"
    return f"{round(bytes_in_curr_dir * BYTE_TO_GIGABYTE, 2)} GB"


@dataclass(slots=True)
class ReportWriter:
    """ReportWriter class for Mandala."""

    root: Path
    exts_str: str
    keys_str: str
    timestamp: DateTimeSingleton
    buffer: list[str] = field(default_factory=list)
    report_path: Path = field(init=False)

    def reset_for_dest(self, dest: Path) -> None:
        """Initialize reporter for a new run."""
        self.buffer.clear()
        self.report_path = dest / f"!_report_{dest.name}.txt"

    def record_message(self, message: str) -> None:
        """Add a message to the buffer."""
        self.buffer.append(f"{message}\n")

    def generate_report(self, dest: Path, status: str, runtime: float, size: int) -> str:
        """Generate the header report string."""
        return (
            "\n========================================================================\n"
            f"{status}\n"
            "========================================================================\n\n"
            f"Date:             {self.timestamp.date_time_report_str}\n"
            f"Root:             {self.root}\n"
            f"Destination:      {dest}\n"
            f"Extensions:       {self.exts_str}\n"
            f"Keywords:         {self.keys_str}\n"
            f"Total size:       {convert_byte_to_size(size)}\n"
            f"Total runtime:    {runtime}s\n"
            "------------------------------------------------------------------------\n"
        )

    def save(self) -> None:
        """Save the report to file."""
        mode = "a" if self.report_path.exists() else "w"
        with self.report_path.open(mode=mode, encoding="utf-8") as f:
            f.writelines(self.buffer)
            f.write("\n\n")
