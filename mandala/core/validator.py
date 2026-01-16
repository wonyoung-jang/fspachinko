"""Config validation functions for Mandala."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

import ffmpeg

if TYPE_CHECKING:
    from pathlib import Path

    from ..config.config import MandalaConfig
    from ..config.schemas import LimitMinMaxModel


def _check_filename(part: str, patterns: tuple[re.Pattern, ...], *, include: bool, exclude: bool) -> bool:
    """Check if a file name part matches the cached regexes."""
    if not patterns:
        return True

    if include:
        if not any(p.search(part) for p in patterns):
            return False
    elif exclude and any(p.search(part) for p in patterns):
        return False

    return True


def _check_range(val: float, model: LimitMinMaxModel) -> bool:
    """Check if a value is within the specified range."""
    if not model.limit:
        return True
    return model.minimum <= val <= model.maximum


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

    config: MandalaConfig
    key_re_cache: tuple[re.Pattern, ...] = ()
    ext_re_cache: tuple[re.Pattern, ...] = ()

    def __post_init__(self) -> None:
        """Post-initialization tasks."""
        self._init_regexes()

    def _init_regexes(self) -> None:
        """Pre-build and cache regex patterns for extensions and keywords."""
        if keys := self.config.keyword.text:
            self.key_re_cache = tuple(re.compile(rf"(.*){k}(.*)", re.IGNORECASE) for k in keys)

        if exts := self.config.extension.text:
            self.ext_re_cache = tuple(re.compile(rf"\.{e}$", re.IGNORECASE) for e in exts)

    def is_valid(self, path: Path, size: int) -> bool:
        """Check if a file is valid based on the current filters."""
        cfg = self.config
        if not _check_range(size, cfg.filesize):
            return False

        if not _check_filename(
            part=path.stem,
            patterns=self.key_re_cache,
            include=cfg.keyword.include,
            exclude=cfg.keyword.exclude,
        ):
            return False

        if not _check_filename(
            part=path.suffix,
            patterns=self.ext_re_cache,
            include=cfg.extension.include,
            exclude=cfg.extension.exclude,
        ):
            return False

        duration = _get_duration(path)
        return _check_range(duration, cfg.duration)
