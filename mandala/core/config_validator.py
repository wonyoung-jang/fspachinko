"""Config validation functions for Mandala."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

import soundfile
from mutagen.mp3 import MP3

if TYPE_CHECKING:
    from pathlib import Path

    from mandala.core.mandala_config import MandalaConfig


@dataclass(slots=True)
class FileValidator:
    """Class for validating files based on configuration."""

    config: MandalaConfig

    def is_valid(self, source: Path, size: int) -> bool:
        """Check if a file is valid based on the current filters."""
        if not self.is_valid_size(size):
            return False

        if self.is_not_extension_or_keyword(source):
            return False

        if not self.is_extension(source):
            return False

        if not self.is_keyword(source):
            return False

        return self.is_within_duration(source)

    def is_valid_size(self, size: int) -> bool:
        """Check if a file is within the specified size range."""
        if not self.config.limit_size:
            return True

        return self.config.min_size <= size <= self.config.max_size

    def is_not_extension_or_keyword(self, source: Path) -> bool:
        """Check if a file has the specified not extensions or not keywords."""
        for not_extension in self.config.not_extensions:
            if re.compile(rf"\.{not_extension}$", re.IGNORECASE).search(source.suffix) is not None:
                return True

        for not_keyword in self.config.not_keywords:
            if re.compile(rf"(.*){not_keyword}(.*)", re.IGNORECASE).search(source.stem) is not None:
                return True

        return False

    def is_extension(self, source: Path) -> bool:
        """Check if a file has the specified extensions."""
        if not self.config.extensions:
            return True

        for extension in self.config.extensions:
            if re.compile(rf"\.{extension}$", re.IGNORECASE).search(source.suffix) is not None:
                return True

        return False

    def is_keyword(self, source: Path) -> bool:
        """Check if a file contains the specified keywords."""
        if not self.config.keywords:
            return True

        for keyword in self.config.keywords:
            if re.compile(rf"(.*){keyword}(.*)", re.IGNORECASE).search(source.stem) is not None:
                return True

        return False

    def is_within_duration(self, source: Path) -> bool:
        """Check if a file is within the specified duration range."""
        if not self.config.limit_duration:
            return True

        duration = 0.0
        min_duration = self.config.min_duration
        max_duration = self.config.max_duration

        try:
            sound = soundfile.SoundFile(source)
            duration = len(sound) / sound.samplerate
        except RuntimeError:
            try:
                if source.suffix == ".mp3":
                    duration = MP3(source).info.length
                    return min_duration <= duration <= max_duration
            except ValueError:
                return True
            else:
                return True
        except ValueError:
            return True

        return min_duration <= duration <= max_duration
