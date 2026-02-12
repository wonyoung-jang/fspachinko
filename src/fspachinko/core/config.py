"""Configuration dataclasses."""

import os
import re
from dataclasses import dataclass, field
from os.path import basename, dirname, exists
from random import randint
from typing import TYPE_CHECKING

from ..core import (
    INVALID_FILENAME_CHARS,
    DateTimeStamp,
    FilenameTemplateMapKey,
    SafeDict,
    are_paths_equal,
    calc_unique_path_name,
    convert_string_to_list,
    get_stem_and_ext,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from .schemas import (
        DirectoryModel,
        FilecountModel,
        FilenameModel,
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
    get_count: Callable[[], int] = field(init=False)

    def __post_init__(self) -> None:
        """Post init to set get_count function."""
        self.get_count = self.get_count_rand if self.is_rand_enabled else lambda: self.count

    @classmethod
    def from_model(cls, m: FilecountModel) -> Filecount:
        """Create Filecount from configuration model."""
        return cls(
            count=m.count,
            is_rand_enabled=m.is_rand_enabled,
            rand_min=m.rand_min,
            rand_max=m.rand_max,
        )

    def get_count_rand(self) -> int:
        """Get the file count based on configuration."""
        return randint(self.rand_min, self.rand_max)


@dataclass(slots=True)
class Filename:
    """Dataclass for file renaming."""

    template: str
    dtstamp: DateTimeStamp

    @classmethod
    def from_model(cls, m: FilenameModel, dtstamp: DateTimeStamp) -> Filename:
        """Create Filename from configuration model."""
        return cls(template=m.template, dtstamp=dtstamp)

    def calc_target_name(self, chosen: str, dest: str, index: int) -> str:
        """Prepare the target file path based on naming conventions."""
        stem, ext = get_stem_and_ext(chosen)

        safe_dict = SafeDict(
            {
                FilenameTemplateMapKey.DATE: self.dtstamp.date,
                FilenameTemplateMapKey.TIME: self.dtstamp.time,
                FilenameTemplateMapKey.DATETIME: self.dtstamp.date_time,
                FilenameTemplateMapKey.ORIGINAL: stem,
                FilenameTemplateMapKey.INDEX: index + 1,
                FilenameTemplateMapKey.PARENT: basename(dirname(chosen)),
                FilenameTemplateMapKey.PARENTS_TO_ROOT: "_".join(chosen.split(os.sep)[:-1]),
            }
        )

        try:
            new_stem = self.template.format_map(safe_dict)
        except (KeyError, ValueError):
            new_stem = stem

        name = "".join(c for c in new_stem if c not in INVALID_FILENAME_CHARS) + ext
        return os.path.join(dest, name)

    def determine_dest_filename(self, chosen: str, dest: str, index: int) -> str | None:
        """Calculate the destination file path based on configuration."""
        target = self.calc_target_name(chosen, dest, index)

        if not exists(target):
            return target

        if are_paths_equal(chosen, target):
            return None

        stem, ext = get_stem_and_ext(target)
        return calc_unique_path_name(dest, stem, ext)


@dataclass(slots=True)
class Folder:
    """Dataclass for folder creation configuration."""

    is_enabled: bool
    dest: str
    name: str
    determine: Callable[[], str] = field(init=False)

    def __post_init__(self) -> None:
        """Post init to set determine_dest function."""
        self.determine = lambda: calc_unique_path_name(self.dest, self.name) if self.is_enabled else lambda: self.dest

    @classmethod
    def from_model(cls, m: DirectoryModel, dest: str) -> Folder:
        """Create Folder from configuration model."""
        return cls(
            is_enabled=m.is_enabled,
            dest=dest,
            name=m.name,
        )


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
        return self.minimum <= value <= self.maximum


@dataclass(slots=True)
class ListIncludeExclude:
    """Dataclass for include-exclude list configuration."""

    is_enabled: bool
    should_include: bool
    as_string: str
    patterns: tuple[re.Pattern, ...]
    is_valid: Callable[[str], bool] = field(init=False)

    def __post_init__(self) -> None:
        """Post init to set validator function."""
        self.is_valid = (
            lambda part: any(pattern.search(part) for pattern in self.patterns)
            if self.should_include
            else lambda part: not any(pattern.search(part) for pattern in self.patterns)
        )

    @classmethod
    def from_model(cls, m: ListIncludeExcludeModel, re_fmt: str) -> ListIncludeExclude:
        """Create ListIncludeExclude from configuration model."""
        as_string = ""
        patterns = ()
        if text := m.text.strip():
            text_list = convert_string_to_list(text)
            as_string = ", ".join(text_list)
            patterns = tuple(re.compile(re_fmt.format(re.escape(i)), re.IGNORECASE) for i in text_list)
        return cls(
            is_enabled=m.is_enabled and bool(text),
            should_include=m.should_include,
            as_string=as_string,
            patterns=patterns,
        )


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
        return self.is_enabled and self.size_limit > 0 and size > self.size_limit

    def get_percent_str(self, size: int) -> str:
        """Get the percentage of the size limit used."""
        return f"{size * 100 / self.size_limit:.2f}%"
