"""Mandala configuration dataclasses."""

import re
from dataclasses import dataclass, field
from filecmp import cmp
from typing import TYPE_CHECKING

from ..utils import INVALID_FILENAME_CHARS, FilenameTemplateMapKeys, SafeDict, calc_unique_path_name

if TYPE_CHECKING:
    from pathlib import Path
    from random import Random

    from ..utils import DateTimeProvider


@dataclass(slots=True)
class Filecount:
    """Dataclass for file count configuration."""

    count: int
    rand_enabled: bool
    rand_min: int
    rand_max: int
    rng: Random

    def get_count(self) -> int:
        """Get the file count based on configuration."""
        if self.rand_enabled:
            return self.rng.randint(self.rand_min, self.rand_max)
        return self.count


@dataclass(slots=True)
class Filename:
    """Dataclass for file renaming."""

    template: str
    timestamp: DateTimeProvider
    _map: SafeDict = field(default_factory=SafeDict)

    def __post_init__(self) -> None:
        """Post-initialization tasks."""
        self.init_mapping()

    def init_mapping(self) -> None:
        """Initialize the mapping dictionary with timestamp values."""
        self._map.update(
            {
                FilenameTemplateMapKeys.DATE: self.timestamp.date,
                FilenameTemplateMapKeys.TIME: self.timestamp.time,
                FilenameTemplateMapKeys.DATETIME: self.timestamp.date_time,
            }
        )

    def get_target(self, chosen: Path, dest: Path, index: int) -> Path:
        """Prepare the target file path based on naming conventions."""
        original_stem = chosen.stem

        self._map.update(
            {
                FilenameTemplateMapKeys.ORIGINAL: original_stem,
                FilenameTemplateMapKeys.INDEX: index + 1,
                FilenameTemplateMapKeys.PARENT: chosen.parent.name,
                FilenameTemplateMapKeys.PARENTS_TO_ROOT: "_".join(chosen.parts[:-1]),
            }
        )

        try:
            stem = self.template.format_map(self._map)
        except (KeyError, ValueError):
            stem = original_stem

        new_stem = "".join(c for c in stem if c not in INVALID_FILENAME_CHARS)
        return dest / f"{new_stem}{chosen.suffix}"

    def calc_dest_target(self, chosen: Path, dest: Path, index: int) -> Path | None:
        """Calculate the destination file path based on naming conventions."""
        target = self.get_target(chosen, dest, index)
        if target.exists():
            if cmp(chosen, target, shallow=True) and cmp(chosen, target, shallow=False):
                return None
            return calc_unique_path_name(dest, target.stem, target.suffix)
        return target


@dataclass(slots=True)
class Folder:
    """Dataclass for folder creation configuration."""

    create_enabled: bool
    name: str
    count: int
    dest: Path

    def create_dest_folder(self) -> Path:
        """Create the destination folder based on configuration."""
        if not self.create_enabled:
            return self.dest

        target = calc_unique_path_name(self.dest, self.name)
        target.mkdir(parents=False)
        return target


@dataclass(slots=True)
class MinMax:
    """Dataclass for min-max limit configuration."""

    enabled: bool
    minimum: float
    maximum: float

    def is_within(self, value: float) -> bool:
        """Check if a value is within the min-max range."""
        if not self.enabled:
            return True
        return self.minimum <= value <= self.maximum


@dataclass(slots=True)
class ListIncludeExclude:
    """Dataclass for include-exclude list configuration."""

    include_enabled: bool
    exclude_enabled: bool
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

        if self.include_enabled:
            if not any(p.search(part) for p in self.patterns):
                return False
        elif self.exclude_enabled and any(p.search(part) for p in self.patterns):
            return False

        return True
