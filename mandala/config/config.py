"""Mandala configuration dataclasses."""

from __future__ import annotations

import re
from dataclasses import dataclass
from filecmp import cmp
from typing import TYPE_CHECKING

from ..utils.helpers import SafeDict, calc_unique_path_name

if TYPE_CHECKING:
    from pathlib import Path
    from random import Random

    from ..core.timestamp import DateTimeSingleton


@dataclass(slots=True)
class Filecount:
    """Dataclass for file count configuration."""

    count: int
    is_rand: bool
    min_rand: int
    max_rand: int
    rng: Random

    def get_count(self) -> int:
        """Get the file count based on configuration."""
        if self.is_rand:
            return self.rng.randint(self.min_rand, self.max_rand)
        return self.count


@dataclass(slots=True)
class Filename:
    """Dataclass for file renaming."""

    template: str
    timestamp: DateTimeSingleton

    def calc_dest_target(self, chosen: Path, dest: Path, index: int) -> Path | None:
        """Calculate the destination file path based on naming conventions."""
        ext = chosen.suffix
        stem = chosen.stem

        mapping = {
            "original": stem,
            "index": index + 1,
            "date": self.timestamp.date,
            "time": self.timestamp.time,
            "datetime": self.timestamp.date_time,
            "parent": chosen.parent.name,
            "parentstoroot": "_".join(chosen.parts[:-1]),
        }
        safe_map = SafeDict(mapping)

        try:
            new_stem = self.template.format_map(safe_map)
        except (KeyError, ValueError):
            new_stem = stem

        invalid_chars = r'\/:*?"<>|'
        new_stem = "".join(c for c in new_stem if c not in invalid_chars)
        name = f"{new_stem}{ext}"

        target = dest / name

        if target.exists():
            if target.stat().st_size == chosen.stat().st_size:
                if cmp(chosen, target, shallow=True) and cmp(chosen, target, shallow=False):
                    return None
            else:
                return calc_unique_path_name(dest, target.stem, ext)
        else:
            return target

        return None


@dataclass(slots=True)
class Folder:
    """Dataclass for folder creation configuration."""

    create: bool
    unique: bool
    name: str
    count: int
    dest: Path

    def create_dest_folder(self) -> Path:
        """Create the destination folder based on configuration."""
        if not self.create:
            return self.dest

        name = self.name
        target = calc_unique_path_name(self.dest, name)
        target.mkdir(parents=False)
        return target


@dataclass(slots=True)
class MinMax:
    """Dataclass for min-max limit configuration."""

    limit: bool
    minimum: float
    maximum: float

    def is_within(self, value: float) -> bool:
        """Check if a value is within the min-max range."""
        if not self.limit:
            return True
        return self.minimum <= value <= self.maximum


@dataclass(slots=True)
class ListIncludeExclude:
    """Dataclass for include-exclude list configuration."""

    include: bool
    exclude: bool
    text: tuple[str, ...]
    re_fmt: str
    as_string: str = ""
    patterns: tuple[re.Pattern, ...] = ()

    def __post_init__(self) -> None:
        """Post-initialization tasks."""
        self._compile_patterns()
        self.as_string = ", ".join(self.text) if self.text else "ALL"

    def _compile_patterns(self) -> None:
        """Compile regex patterns based on the text list."""
        if not self.text:
            self.patterns = ()
        else:
            self.patterns = tuple(re.compile(self.re_fmt.format(i), re.IGNORECASE) for i in self.text)

    def is_matched(self, part: str) -> bool:
        """Check if a file name part matches the cached regexes."""
        if not self.patterns:
            return True

        if self.include:
            if not any(p.search(part) for p in self.patterns):
                return False
        elif self.exclude and any(p.search(part) for p in self.patterns):
            return False

        return True
