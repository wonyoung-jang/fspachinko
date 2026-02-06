"""Reporter for process."""

import os
from dataclasses import dataclass, field

from ..utils import DateTimeStamp, convert_byte_to_human_readable_size


@dataclass(slots=True)
class ReportWriter:
    """ReportWriter class."""

    root: str
    exts_str: str
    keys_str: str
    dtstamp: DateTimeStamp
    buffer: list[str] = field(default_factory=list)
    dest: str = field(init=False)

    def reset(self, dest: str) -> None:
        """Initialize reporter for a new run."""
        self.buffer.clear()
        self.dest = dest

    def record(self, message: str) -> None:
        """Add a message to the buffer."""
        self.buffer.append(f"{message}\n")

    def generate_report(self, status: str, runtime: float, size: int) -> str:
        """Generate the header report string."""
        report = (
            f"\n{status}"
            "\n------------------------------------------------------------------------\n"
            f"Timestamp:    {self.dtstamp.date_time_report_str}\n"
            f"Root:         {self.root}\n"
            f"Destination:  {self.dest}\n"
            f"Extension:    {self.exts_str}\n"
            f"Keyword:      {self.keys_str}\n"
            f"Size:         {convert_byte_to_human_readable_size(size)}\n"
            f"Runtime:      {runtime}s\n"
            "\n========================================================================\n"
            "========================================================================\n"
            "========================================================================\n"
            "========================================================================\n"
            "========================================================================\n"
        )
        self.buffer.insert(0, report)
        return report

    def save(self) -> None:
        """Save the report to file."""
        report_path = os.path.join(self.dest, f"!_{os.path.basename(self.dest)}_report.txt")
        mode = "a" if os.path.exists(report_path) else "w"
        with open(report_path, mode=mode, encoding="utf-8") as f:
            f.writelines(self.buffer)
            f.write("\n\n")
