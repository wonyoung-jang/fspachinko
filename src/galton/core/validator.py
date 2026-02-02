"""Config validation functions."""

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING

from ffmpeg import Error as FFmpegError
from ffmpeg import probe as ffprobe

if TYPE_CHECKING:
    from ..config import ListIncludeExclude, MinMax


@lru_cache(maxsize=1024)
def _get_duration(path: str) -> float:
    """Get the duration of a media file."""
    try:
        probe = ffprobe(
            filename=path,
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

    def is_valid(self, entry: os.DirEntry) -> bool:
        """Check if a file is valid based on the current filters."""
        if self.filesize.is_enabled and not self.filesize.is_valid(entry.stat().st_size):
            return False

        stem, ext = os.path.splitext(entry.name)

        if self.keywords.is_enabled and not self.keywords.is_valid(stem):
            return False

        return not (self.extensions.is_enabled and not self.extensions.is_valid(ext))

    def is_valid_duration(self, entry: os.DirEntry) -> bool:
        """Check if a file is valid based on the current filters."""
        duration = _get_duration(entry.path)
        return self.duration.is_enabled and self.duration.is_valid(duration)
