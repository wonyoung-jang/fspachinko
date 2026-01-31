"""File Roulette configuration dataclasses."""

import os
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..utils import (
    INVALID_FILENAME_CHARS,
    DateTimeStamp,
    FilenameTemplateMapKeys,
    SafeDict,
    are_paths_equal,
    calc_unique_path_name,
    convert_string_to_list,
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

    def get_file_count(self) -> int:
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
        stem, ext = os.path.splitext(name)

        self._map.update(
            {
                FilenameTemplateMapKeys.DATE: DateTimeStamp.date,
                FilenameTemplateMapKeys.TIME: DateTimeStamp.time,
                FilenameTemplateMapKeys.DATETIME: DateTimeStamp.date_time,
                FilenameTemplateMapKeys.ORIGINAL: stem,
                FilenameTemplateMapKeys.INDEX: index + 1,
                FilenameTemplateMapKeys.PARENT: os.path.basename(os.path.dirname(chosen)),
                FilenameTemplateMapKeys.PARENTS_TO_ROOT: "_".join(chosen.split(os.sep)[:-1]),
            }
        )

        try:
            new_stem = self.template.format_map(self._map)
        except (KeyError, ValueError):
            new_stem = stem

        new_stem = "".join(c for c in new_stem if c not in INVALID_FILENAME_CHARS)
        return os.path.join(dest, f"{new_stem}{ext}")

    def determine_dest_filename(self, chosen: str, dest: str, index: int) -> str | None:
        """Calculate the destination file path based on configuration."""
        target = self._get_target(chosen, dest, index)

        if not os.path.exists(target):
            return target

        if are_paths_equal(chosen, target):
            return None

        name = os.path.basename(target)
        stem, ext = os.path.splitext(name)
        return calc_unique_path_name(dest, stem, ext)


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
        return cls(
            should_create=m.should_create,
            name=m.name,
            count=m.count,
            dest=dest,
        )

    def determine_dest_dirname(self) -> str:
        """Calculate the destination directory name based on configuration."""
        if not self.should_create:
            return self.dest
        return calc_unique_path_name(self.dest, self.name)


@dataclass(slots=True)
class MinMax:
    """Dataclass for min-max limit configuration."""

    is_enabled: bool
    minimum: float
    maximum: float

    @classmethod
    def from_model(cls, m: MinMaxModel, mapping: dict[str, float]) -> MinMax:
        """Create MinMax from configuration model."""
        return cls(
            is_enabled=m.is_enabled,
            minimum=m.minimum * mapping.get(m.unit, 1.0),
            maximum=m.maximum * mapping.get(m.unit, 1.0),
        )

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
    def from_model(cls, m: SizeLimitModel, mapping: dict[str, float]) -> SizeLimit:
        """Create SizeLimit from configuration model."""
        return cls(
            is_enabled=m.is_enabled,
            size_limit=m.size_limit * mapping.get(m.unit, 1.0),
        )

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

    is_enabled: bool
    should_include: bool
    text: str
    as_string: str
    patterns: tuple[re.Pattern, ...]

    @classmethod
    def from_model(cls, m: ListIncludeExcludeModel, re_fmt: str) -> ListIncludeExclude:
        """Create ListIncludeExclude from configuration model."""
        as_string = ""
        patterns = ()
        if m.text:
            text_list = convert_string_to_list(m.text)
            as_string = ", ".join(text_list)
            patterns = tuple(re.compile(re_fmt.format(re.escape(i)), re.IGNORECASE) for i in text_list)
        return cls(
            is_enabled=m.is_enabled,
            should_include=m.should_include,
            text=m.text,
            as_string=as_string,
            patterns=patterns,
        )

    def is_valid(self, part: str) -> bool:
        """Check if a file name part matches the cached regexes."""
        if not self.text:
            return True

        if self.should_include:
            return any(p.search(part) for p in self.patterns)
        return not any(p.search(part) for p in self.patterns)
