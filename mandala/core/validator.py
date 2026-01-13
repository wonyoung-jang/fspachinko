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

        return self._check_duration(path)

    def _get_ext_regex(self, extension: str) -> re.Pattern:
        """Get a compiled regex pattern for a file extension."""
        pattern = rf"\.{extension}$"
        ext_key = f"ext::{extension}"
        return self.regex_cache.setdefault(ext_key, re.compile(pattern, re.IGNORECASE))

    def _get_key_regex(self, keyword: str) -> re.Pattern:
        """Get a compiled regex pattern for a keyword."""
        pattern = rf"(.*){keyword}(.*)"
        key_key = f"key::{keyword}"
        return self.regex_cache.setdefault(key_key, re.compile(pattern, re.IGNORECASE))

    def _check_size(self, size: int) -> bool:
        """Check if a file is within the specified size range."""
        if not self.config.size_model.limit:
            return True
        return self.config.size_model.minimum <= size <= self.config.size_model.maximum

    def _check_name(self, source: Path) -> bool:
        """Check if a file has the specified not extensions or not keywords."""
        if self._check_keywords(source) is False:
            return False
        return self._check_extensions(source) is not False

    def _check_keywords(self, source: Path) -> bool:
        """Check if a file has the specified keywords."""
        stem = source.stem
        if keys := self.config.keywords_model.text:
            if self.config.keywords_model.include:
                for k in keys:
                    if self._get_key_regex(k).search(stem) is None:
                        return False
            elif self.config.keywords_model.exclude:
                for nk in keys:
                    if self._get_key_regex(nk).search(stem) is not None:
                        return False
        return True

    def _check_extensions(self, source: Path) -> bool:
        """Check if a file has the specified extensions."""
        suffix = source.suffix
        if exts := self.config.extensions_model.text:
            if self.config.extensions_model.include:
                for e in exts:
                    if self._get_ext_regex(e).search(suffix) is None:
                        return False
            elif self.config.extensions_model.exclude:
                for ne in exts:
                    if self._get_ext_regex(ne).search(suffix) is not None:
                        return False
        return True

    def _check_duration(self, source: Path) -> bool:
        """Check if a file is within the specified duration range."""
        if not self.config.duration_model.limit:
            return True

        try:
            probe = ffmpeg.probe(
                filename=str(source),
                cmd="ffprobe",
            )
            duration = float(probe["format"]["duration"])
        except (ValueError, KeyError, ffmpeg.Error):
            return True

        return self.config.duration_model.minimum <= duration <= self.config.duration_model.maximum
