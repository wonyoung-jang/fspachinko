"""Config validation functions for Mandala."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import ffmpeg

if TYPE_CHECKING:
    from pathlib import Path

    from ..config.config import ListIncludeExclude, MinMax


def _get_duration(path: Path) -> float:
    """Get the duration of a media file."""
    try:
        probe = ffmpeg.probe(
            filename=str(path),
            cmd="ffprobe",
            select_streams="v:0",
            show_entries="format=duration",
        )
        return float(probe["format"]["duration"])
    except (ValueError, KeyError, ffmpeg.Error):
        return 0.0


@dataclass(slots=True)
class FileValidator:
    """Class for validating files based on configuration."""

    keywords: ListIncludeExclude
    extensions: ListIncludeExclude
    filesize: MinMax
    duration: MinMax

    def is_valid(self, path: Path, size: int) -> bool:
        """Check if a file is valid based on the current filters."""
        if not self.filesize.is_within(size):
            return False

        if not self.extensions.is_matched(path.suffix):
            return False

        if not self.keywords.is_matched(path.stem):
            return False

        duration = _get_duration(path)
        return self.duration.is_within(duration)
