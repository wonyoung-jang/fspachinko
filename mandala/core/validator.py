"""Config validation functions for Mandala."""

import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ffmpeg import Error as FFmpegError
from ffmpeg import probe as ffprobe

if TYPE_CHECKING:
    from ..config import ListIncludeExclude, MinMax


def _get_duration(path: str) -> float:
    """Get the duration of a media file."""
    try:
        probe = ffprobe(
            filename=path,
            select_streams="v:0",
            show_entries="format=duration",
        )
        return float(probe["format"]["duration"])
    except (ValueError, KeyError, FFmpegError):
        return 0.0


@dataclass(slots=True)
class FileValidator:
    """Class for validating files based on configuration."""

    keywords: ListIncludeExclude
    extensions: ListIncludeExclude
    filesize: MinMax
    duration: MinMax
    _duration_cache: dict[str, float] = field(default_factory=dict)

    def is_valid(self, path: str, size: int) -> bool:
        """Check if a file is valid based on the current filters."""
        if not self.filesize.is_valid(size):
            return False

        name = os.path.basename(path)
        stem, ext = os.path.splitext(name)

        if not self.extensions.is_valid(ext):
            return False

        if not self.keywords.is_valid(stem):
            return False

        duration = self._duration_cache.setdefault(path, _get_duration(path))
        return self.duration.is_valid(duration)
