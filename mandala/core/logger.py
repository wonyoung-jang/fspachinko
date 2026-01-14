"""Logger for Mandala process."""

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
class MandalaLogger:
    """Logger class for Mandala."""

    config: MandalaConfig
    state: MandalaState

    buffer: list[str] = field(default_factory=list)

    log_path: Path = field(init=False)

    def reset_for_dest(self, dest: Path) -> None:
        """Initialize logger for a new run."""
        self.buffer.clear()
        self.log_path = dest / f"!{dest.name}_log.txt"

    def log_message(self, message: str) -> None:
        """Log a message to the buffer."""
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
        """Save the log to file."""
        new_content = report + "\n".join(self.buffer) + "\n\n"
        old_content = ""
        if self.log_path.exists():
            with contextlib.suppress(OSError):
                old_content = self.log_path.read_text(encoding="utf-8")

        final_content = new_content + old_content
        with self.log_path.open("w", encoding="utf-8") as log_file:
            log_file.write(final_content)
