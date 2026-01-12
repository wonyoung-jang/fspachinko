"""Config validation functions for Mandala."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import ffmpeg

if TYPE_CHECKING:
    from pathlib import Path

    from .config import MandalaConfig


@dataclass(slots=True)
class FileValidator:
    """Class for validating files based on configuration."""

    config: MandalaConfig
    regex_cache: dict[str, re.Pattern] = field(default_factory=dict)

    def is_valid(self, path: Path, size: int) -> bool:
        """Check if a file is valid based on the current filters."""
        if not self._check_size(size):
            return False

        if not self._check_name(path):
            return False

        if self.config.limit_duration:
            return self._check_duration(path)

        return True

    def _get_ext_regex(self, extension: str) -> re.Pattern:
        """Get a compiled regex pattern for a file extension."""
        pattern = rf"\.{extension}$"
        return self.regex_cache.setdefault(pattern, re.compile(pattern, re.IGNORECASE))

    def _get_key_regex(self, keyword: str) -> re.Pattern:
        """Get a compiled regex pattern for a keyword."""
        pattern = rf"(.*){keyword}(.*)"
        return self.regex_cache.setdefault(pattern, re.compile(pattern, re.IGNORECASE))

    def _check_size(self, size: int) -> bool:
        """Check if a file is within the specified size range."""
        if not self.config.limit_size:
            return True
        return self.config.min_size <= size <= self.config.max_size

    def _check_name(self, source: Path) -> bool:
        """Check if a file has the specified not extensions or not keywords."""
        not_exts = self.config.not_extensions
        not_keys = self.config.not_keywords
        exts = self.config.extensions
        keys = self.config.keywords
        suffix = source.suffix
        stem = source.stem

        if self.config.is_not_extensions and not_exts:
            for ne in not_exts:
                if self._get_ext_regex(ne).search(suffix) is not None:
                    return False

        if self.config.is_not_keywords and not_keys:
            for nk in not_keys:
                if self._get_key_regex(nk).search(stem) is not None:
                    return False

        if self.config.is_extensions and exts:
            for e in exts:
                if self._get_ext_regex(e).search(suffix) is None:
                    return False

        if self.config.is_keywords and keys:
            for k in keys:
                if self._get_key_regex(k).search(stem) is None:
                    return False

        return True

    def _check_duration(self, source: Path) -> bool:
        """Check if a file is within the specified duration range."""
        try:
            probe = ffmpeg.probe(
                filename=str(source),
                cmd="ffprobe",
                verbose="quiet",
                print_format="json",
                show_format=True,
            )
            duration = float(probe["format"]["duration"])
        except (ValueError, KeyError, ffmpeg.Error):
            return True
        return self.config.min_duration <= duration <= self.config.max_duration
