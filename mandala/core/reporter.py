"""Reporter for Mandala process."""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from ..utilities.utils import convert_byte_to_size

if TYPE_CHECKING:
    from pathlib import Path

    from .config import MandalaConfig
    from .state import MandalaState


@dataclass(slots=True)
class ReportWriter:
    """ReportWriter class for Mandala."""

    config: MandalaConfig
    state: MandalaState

    buffer: list[str] = field(default_factory=list)

    report_path: Path = field(init=False)

    def reset_for_dest(self, dest: Path) -> None:
        """Initialize reporter for a new run."""
        self.buffer.clear()
        self.report_path = dest / f"!{dest.name}_report.txt"

    def record_message(self, message: str) -> None:
        """Add a message to the buffer."""
        self.buffer.append(message)

    def generate_report(self, dest: Path, status: str, runtime: float) -> str:
        """Generate the header report string."""
        exts = self.config.extension.text
        keys = self.config.keyword.text
        ext_str = ", ".join(exts) if exts else "ALL"
        kw_str = ", ".join(keys) if keys else "ALL"
        return (
            "\n========================================================================\n"
            f"{status}\n"
            "========================================================================\n\n"
            f"Date:             {datetime.now(tz=UTC).strftime('%B %d, %Y')}\n"
            f"Time:             {datetime.now(tz=UTC).strftime('%I:%M:%S%p')}\n"
            f"Start:            {self.config.root}\n"
            f"Destination:      {dest}\n"
            f"Extensions:       {ext_str}\n"
            f"Keywords:         {kw_str}\n"
            f"Total size:       {convert_byte_to_size(self.state.bytes_in_currdir)}\n"
            f"Total runtime:    {runtime}s\n"
            "------------------------------------------------------------------------\n"
        )

    def save(self, report: str) -> None:
        """Save the report to file."""
        content = report + "\n".join(self.buffer) + "\n\n"
        if self.report_path.exists():
            with contextlib.suppress(OSError):
                content += self.report_path.read_text(encoding="utf-8")

        with self.report_path.open("w", encoding="utf-8") as f:
            f.write(content)
