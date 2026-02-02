"""Config validation functions."""

from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING

from ffmpeg import Error as FFmpegError
from ffmpeg import probe as ffprobe

from ..utils import get_stem_and_ext

if TYPE_CHECKING:
    from ..config import ListIncludeExclude, MinMax


@lru_cache(maxsize=1024)
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

    def is_valid(self, path: str, size: int) -> bool:
        """Check if a file is valid based on the current filters."""
        if self.filesize.is_enabled and not self.filesize.is_valid(size):
            return False

        stem, ext = get_stem_and_ext(path)

        if self.extensions.is_enabled and not self.extensions.is_valid(ext):
            return False

        if self.keywords.is_enabled and not self.keywords.is_valid(stem):
            return False

        duration = _get_duration(path)
        return self.duration.is_enabled and self.duration.is_valid(duration)
