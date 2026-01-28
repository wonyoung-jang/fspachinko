"""Reporter for Mandala process."""

import os
from dataclasses import dataclass, field

from ..utils import convert_byte_to_size, date_time_report_str


@dataclass(slots=True)
class ReportWriter:
    """ReportWriter class for Mandala."""

    root: str
    exts_str: str
    keys_str: str
    buffer: list[str] = field(default_factory=list)
    report_path: str = field(init=False)
    _dest: str = field(init=False)

    def reset_for_dest(self, dest: str) -> None:
        """Initialize reporter for a new run."""
        self.buffer.clear()
        self.report_path = os.path.join(dest, f"!_report_{os.path.basename(dest)}.txt")
        self._dest = dest

    def record_message(self, message: str) -> None:
        """Add a message to the buffer."""
        self.buffer.append(f"{message}\n")

    def generate_report(self, status: str, runtime: float, size: int) -> str:
        """Generate the header report string."""
        return (
            f"\n{status}"
            "\n------------------------------------------------------------------------\n"
            f"Date:             {date_time_report_str}\n"
            f"Root:             {self.root}\n"
            f"Destination:      {self._dest}\n"
            f"Extensions:       {self.exts_str}\n"
            f"Keywords:         {self.keys_str}\n"
            f"Total size:       {convert_byte_to_size(size)}\n"
            f"Total runtime:    {runtime}s\n"
            "\n========================================================================\n"
            "========================================================================\n"
            "========================================================================\n"
            "========================================================================\n"
            "========================================================================\n"
        )

    def save(self) -> None:
        """Save the report to file."""
        mode = "a" if os.path.exists(self.report_path) else "w"
        with open(self.report_path, mode=mode, encoding="utf-8") as f:
            f.writelines(self.buffer)
            f.write("\n\n")
