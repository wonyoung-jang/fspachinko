"""Reporter for process."""

import os
from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core import DateTimeStamp


@dataclass(slots=True)
class ReportWriter:
    """ReportWriter class."""

    root: str
    dtstamp: DateTimeStamp
    buffer: deque[str] = field(default_factory=deque)
    dest: str = field(init=False)

    def reset(self, dest: str) -> None:
        """Initialize reporter for a new run."""
        self.dest = dest

    def record(self, message: str) -> None:
        """Add a message to the buffer."""
        self.buffer.append(f"{message}\n")

    def generate_report(self, status: str, runtime: str, size: str) -> str:
        """Generate the header report string."""
        report = (
            f"\n{status}"
            "\n------------------------------------------------------------------------\n"
            f"Timestamp:    {self.dtstamp.date_time_report_str}\n"
            f"Root:         {self.root}\n"
            f"Destination:  {self.dest}\n"
            f"Size:         {size}\n"
            f"Runtime:      {runtime}\n"
            "\n========================================================================\n"
        )
        self.buffer.appendleft(report)
        return report

    def save(self) -> None:
        """Save the report to file."""
        report_path = os.path.join(self.dest, f"!_{os.path.basename(self.dest)}_report.txt")
        mode = "a" if os.path.exists(report_path) else "w"
        with open(report_path, mode=mode, encoding="utf-8") as f:
            while self.buffer:
                line = self.buffer.popleft()
                f.write(line)
            f.write("\n\n")
