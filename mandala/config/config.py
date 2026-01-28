"""Mandala configuration dataclasses."""

import os
import re
from dataclasses import dataclass, field
from filecmp import cmp
from functools import cache
from typing import TYPE_CHECKING

from ..utils import (
    INVALID_FILENAME_CHARS,
    FilenameTemplateMapKeys,
    SafeDict,
    calc_unique_path_name,
    date,
    date_time,
    time,
)

if TYPE_CHECKING:
    from random import Random

    from .schemas import (
        FilecountModel,
        FilenameModel,
        FolderModel,
        ListIncludeExcludeModel,
        MinMaxModel,
        SizeLimitModel,
    )


@dataclass(slots=True)
class Filecount:
    """Dataclass for file count configuration."""

    count: int
    rand_enabled: bool
    rand_min: int
    rand_max: int
    rng: Random

    @classmethod
    def from_model(cls, m: FilecountModel, rng: Random) -> Filecount:
        """Create Filecount from configuration model."""
        return cls(count=m.count, rand_enabled=m.rand_enabled, rand_min=m.rand_min, rand_max=m.rand_max, rng=rng)

    def get_count(self) -> int:
        """Get the file count based on configuration."""
        if self.rand_enabled:
            return self.rng.randint(self.rand_min, self.rand_max)
        return self.count


@dataclass(slots=True)
class Filename:
    """Dataclass for file renaming."""

    template: str
    _map: SafeDict = field(default_factory=SafeDict)

    @classmethod
    def from_model(cls, m: FilenameModel) -> Filename:
        """Create Filename from configuration model."""
        return cls(template=m.template)

    def _get_target(self, chosen: str, dest: str, index: int) -> str:
        """Prepare the target file path based on naming conventions."""
        name = os.path.basename(chosen)
        original_stem, ext = os.path.splitext(name)

        self._map.update(
            {
                FilenameTemplateMapKeys.DATE: date,
                FilenameTemplateMapKeys.TIME: time,
                FilenameTemplateMapKeys.DATETIME: date_time,
                FilenameTemplateMapKeys.ORIGINAL: original_stem,
                FilenameTemplateMapKeys.INDEX: index + 1,
                FilenameTemplateMapKeys.PARENT: os.path.basename(os.path.dirname(chosen)),
                FilenameTemplateMapKeys.PARENTS_TO_ROOT: "_".join(chosen.split(os.sep)[:-1]),
            }
        )

        try:
            stem = self.template.format_map(self._map)
        except (KeyError, ValueError):
            stem = original_stem

        new_stem = "".join(c for c in stem if c not in INVALID_FILENAME_CHARS)
        return os.path.join(dest, f"{new_stem}{ext}")

    def calc_dest_target(self, chosen: str, dest: str, index: int) -> str | None:
        """Calculate the destination file path based on naming conventions."""
        target = self._get_target(chosen, dest, index)
        if os.path.exists(target):
            if cmp(chosen, target, shallow=True) and cmp(chosen, target, shallow=False):
                return None
            name = os.path.basename(target)
            stem, ext = os.path.splitext(name)
            return calc_unique_path_name(dest, stem, ext)
        return target


@dataclass(slots=True)
class Folder:
    """Dataclass for folder creation configuration."""

    create_enabled: bool
    name: str
    count: int
    dest: str

    @classmethod
    def from_model(cls, m: FolderModel, dest: str) -> Folder:
        """Create Folder from configuration model."""
        return cls(create_enabled=m.create_enabled, name=m.name, count=m.count, dest=dest)

    def create_dest_folder(self) -> str:
        """Create the destination folder based on configuration."""
        if not self.create_enabled:
            return self.dest

        target = calc_unique_path_name(self.dest, self.name)
        os.mkdir(target)
        return target


@dataclass(slots=True)
class MinMax:
    """Dataclass for min-max limit configuration."""

    enabled: bool
    minimum: float
    maximum: float

    @classmethod
    def from_model(cls, m: MinMaxModel) -> MinMax:
        """Create MinMax from configuration model."""
        return cls(enabled=m.enabled, minimum=m.minimum, maximum=m.maximum)

    def is_valid(self, value: float) -> bool:
        """Check if a value is within the min-max range."""
        if not self.enabled:
            return True
        return self.minimum <= value <= self.maximum


@dataclass(slots=True)
class SizeLimit:
    """Dataclass for output folder size limits."""

    enabled: bool
    size_limit: float

    @classmethod
    def from_model(cls, m: SizeLimitModel) -> SizeLimit:
        """Create SizeLimit from configuration model."""
        return cls(enabled=m.enabled, size_limit=m.size_limit)

    def is_valid(self, size: int) -> bool:
        """Check if the size limit is exceeded."""
        if not self.enabled or self.size_limit <= 0:
            return False
        return size > self.size_limit


@cache
def compile_re(re_fmt: str, text: str) -> re.Pattern:
    """Compile a regex pattern.

    Cached to avoid recompilation of the same pattern.
    """
    return re.compile(re_fmt.format(re.escape(text)), re.IGNORECASE)


@dataclass(slots=True)
class ListIncludeExclude:
    """Dataclass for include-exclude list configuration."""

    include_enabled: bool
    exclude_enabled: bool
    text: tuple[str, ...]
    re_fmt: str
    as_string: str = "ALL"
    patterns: tuple[re.Pattern, ...] = ()

    def __post_init__(self) -> None:
        """Post-initialization tasks."""
        self._precompile()

    @classmethod
    def from_model(cls, m: ListIncludeExcludeModel, re_fmt: str) -> ListIncludeExclude:
        """Create ListIncludeExclude from configuration model."""
        return cls(
            include_enabled=m.include_enabled, exclude_enabled=m.exclude_enabled, text=tuple(m.text), re_fmt=re_fmt
        )

    def _precompile(self) -> None:
        """Compile regex patterns based on the text list."""
        if self.text:
            self.as_string = ", ".join(self.text)
            self.patterns = tuple(compile_re(self.re_fmt, i) for i in self.text)

    def is_valid(self, part: str) -> bool:
        """Check if a file name part matches the cached regexes."""
        if not self.patterns:
            return True

        if self.exclude_enabled:
            return any(p.search(part) for p in self.patterns)
        return any(p.search(part) for p in self.patterns)
