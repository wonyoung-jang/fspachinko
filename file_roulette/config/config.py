"""File Roulette configuration dataclasses."""

import os
import re
from dataclasses import dataclass, field
from filecmp import cmp
from typing import TYPE_CHECKING

from ..utils import (
    INVALID_FILENAME_CHARS,
    FilenameTemplateMapKeys,
    SafeDict,
    calc_unique_path_name,
    convert_string_to_list,
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
    is_rand_enabled: bool
    rand_min: int
    rand_max: int
    rng: Random

    @classmethod
    def from_model(cls, m: FilecountModel, rng: Random) -> Filecount:
        """Create Filecount from configuration model."""
        return cls(count=m.count, is_rand_enabled=m.is_rand_enabled, rand_min=m.rand_min, rand_max=m.rand_max, rng=rng)

    def get_count(self) -> int:
        """Get the file count based on configuration."""
        if self.is_rand_enabled:
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

    should_create: bool
    name: str
    count: int
    dest: str

    @classmethod
    def from_model(cls, m: FolderModel, dest: str) -> Folder:
        """Create Folder from configuration model."""
        return cls(should_create=m.should_create, name=m.name, count=m.count, dest=dest)

    def create_dest_folder(self) -> str:
        """Create the destination folder based on configuration."""
        if not self.should_create:
            return self.dest

        target = calc_unique_path_name(self.dest, self.name)
        os.mkdir(target)
        return target


@dataclass(slots=True)
class MinMax:
    """Dataclass for min-max limit configuration."""

    is_enabled: bool
    minimum: float
    maximum: float

    @classmethod
    def from_model(cls, m: MinMaxModel) -> MinMax:
        """Create MinMax from configuration model."""
        return cls(is_enabled=m.is_enabled, minimum=m.minimum, maximum=m.maximum)

    def is_valid(self, value: float) -> bool:
        """Check if a value is within the min-max range."""
        if not self.is_enabled:
            return True
        return self.minimum <= value <= self.maximum


@dataclass(slots=True)
class SizeLimit:
    """Dataclass for output folder size limits."""

    is_enabled: bool
    size_limit: float

    @classmethod
    def from_model(cls, m: SizeLimitModel) -> SizeLimit:
        """Create SizeLimit from configuration model."""
        return cls(is_enabled=m.is_enabled, size_limit=m.size_limit)

    def is_valid(self, size: int) -> bool:
        """Check if the size limit is exceeded."""
        if not self.is_enabled:
            return False

        if self.size_limit <= 0:
            return False

        return size > self.size_limit


@dataclass(slots=True)
class ListIncludeExclude:
    """Dataclass for include-exclude list configuration."""

    should_include: bool
    text: str
    re_fmt: str
    as_string: str = "ALL"
    patterns: tuple[re.Pattern, ...] = ()

    def __post_init__(self) -> None:
        """Post-initialization tasks."""
        self._precompile()

    @classmethod
    def from_model(cls, m: ListIncludeExcludeModel, re_fmt: str) -> ListIncludeExclude:
        """Create ListIncludeExclude from configuration model."""
        return cls(should_include=m.should_include, text=m.text, re_fmt=re_fmt)

    def _precompile(self) -> None:
        """Compile regex patterns based on the text list."""
        if self.text:
            text_list = convert_string_to_list(self.text)
            self.as_string = ", ".join(text_list)
            self.patterns = tuple(re.compile(self.re_fmt.format(re.escape(i)), re.IGNORECASE) for i in text_list)

    def is_valid(self, part: str) -> bool:
        """Check if a file name part matches the cached regexes."""
        if not self.text:
            return True

        if self.should_include:
            return any(p.search(part) for p in self.patterns)
        return not any(p.search(part) for p in self.patterns)
