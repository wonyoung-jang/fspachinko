"""Mandala configuration dataclasses."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
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
    _mapping: SafeDict = field(default_factory=SafeDict)
    _invalid_chars: str = r'\/:*?"<>|'

    def __post_init__(self) -> None:
        """Post-initialization tasks."""
        self.init_mapping()

    def init_mapping(self) -> None:
        """Initialize the mapping dictionary with timestamp values."""
        self._mapping.update(
            {
                "date": self.timestamp.date,
                "time": self.timestamp.time,
                "datetime": self.timestamp.date_time,
            }
        )

    def get_target(self, chosen: Path, dest: Path, index: int) -> Path:
        """Prepare the target file path based on naming conventions."""
        original_stem = chosen.stem

        self._mapping.update(
            {
                "original": original_stem,
                "index": index + 1,
                "parent": chosen.parent.name,
                "parentstoroot": "_".join(chosen.parts[:-1]),
            }
        )

        try:
            new_stem = self.template.format_map(self._mapping)
        except (KeyError, ValueError):
            new_stem = original_stem

        new_stem = "".join(c for c in new_stem if c not in self._invalid_chars)
        name = f"{new_stem}{chosen.suffix}"

        return dest / name

    def calc_dest_target(self, chosen: Path, dest: Path, index: int) -> Path | None:
        """Calculate the destination file path based on naming conventions."""
        target = self.get_target(chosen, dest, index)
        if target.exists():
            if cmp(chosen, target, shallow=True):
                return None
            if cmp(chosen, target, shallow=False):
                return None
            return calc_unique_path_name(dest, target.stem, target.suffix)
        return target


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
