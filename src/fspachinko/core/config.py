"""Configuration dataclasses."""

import os
import re
from dataclasses import dataclass
from os.path import basename, dirname, exists, isabs, join, realpath
from random import randint
from typing import TYPE_CHECKING

from pydantic import BaseModel, field_validator

from .constants import FilenameTemplateMapKey, TransferMode
from .helpers import (
    SafeDict,
    are_paths_equal,
    calc_unique_path_name,
    convert_string_to_list,
    get_stem_and_ext,
    get_valid_filename_from_str,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from .context import DateTimeStamp


class FilecountModel(BaseModel):
    """Model for file count configuration."""

    count: int = 0
    is_rand_enabled: bool = False
    rand_min: int = 0
    rand_max: int = 0

    def get_count_fn(self) -> Callable[[], int]:
        """Return a function that determines the number of files to transfer based on the configuration."""
        return (lambda: randint(self.rand_min, self.rand_max)) if self.is_rand_enabled else (lambda: self.count)


class DirectoryModel(BaseModel):
    """Model for directory creation configuration."""

    is_enabled: bool = False
    name: str = ""
    count: int = 1

    def get_dirname_fn(self, dest: str) -> Callable[[], str]:
        """Return a function that determines the destination folder name based on the configuration."""
        return (lambda: calc_unique_path_name(dest, self.name)) if self.is_enabled else (lambda: dest)


class FilenameModel(BaseModel):
    """Model for file renaming."""

    is_enabled: bool = False
    template: str = "{original}"


class ListIncludeExcludeModel(BaseModel):
    """Model for list filtering."""

    is_enabled: bool = True
    should_include: bool = True
    text: str = ""


class MinMaxModel(BaseModel):
    """Model for size filter."""

    is_enabled: bool = False
    minimum: float = 0.0
    maximum: float = 0.0
    unit: str = ""


class OptionsModel(BaseModel):
    """Model for additional options."""

    transfer_mode: str = TransferMode.SYMLINK
    max_per_folder: int = 0
    is_create_unique_folders: bool = False
    should_follow_symlink: bool = False
    is_dry_run: bool = True
    rng_seed: int | str | bytes | None = None


class ConfigModel(BaseModel):
    """Model for  configuration."""

    root: str
    dest: str
    filecount: FilecountModel
    folder: DirectoryModel
    filename: FilenameModel
    directory_name: ListIncludeExcludeModel
    keyword: ListIncludeExcludeModel
    extension: ListIncludeExcludeModel
    filesize: MinMaxModel
    duration: MinMaxModel
    options: OptionsModel

    @field_validator("root", "dest")
    @classmethod
    def is_absolute(cls, val: str) -> str:
        """Ensure root and dest paths are absolute."""
        if not isabs(val):
            return realpath(val)
        return val


# Config logic


@dataclass(slots=True)
class Filename:
    """Dataclass for file renaming."""

    template: str
    dtstamp: DateTimeStamp

    def __call__(self, chosen: str, dest: str, index: int) -> str | None:
        """Calculate the destination file path based on configuration."""
        stem, ext = get_stem_and_ext(chosen)
        mapping = SafeDict(
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
            formatted_stem = self.template.format_map(mapping)
            new_stem = get_valid_filename_from_str(formatted_stem)
        except KeyError, ValueError:
            new_stem = stem

        name = new_stem + ext
        target = join(dest, name)
        if not exists(target):
            return target
        if are_paths_equal(chosen, target):
            return None
        return calc_unique_path_name(dest, new_stem, ext)

    @classmethod
    def from_model(cls, m: FilenameModel, dtstamp: DateTimeStamp) -> Filename:
        """Create Filename from configuration model."""
        return cls(template=m.template, dtstamp=dtstamp)


@dataclass(slots=True)
class ListIncludeExclude:
    """Dataclass for include-exclude list configuration."""

    is_enabled: bool
    is_valid: Callable[[str], bool]

    @classmethod
    def from_model(cls, m: ListIncludeExcludeModel, re_fmt: str) -> ListIncludeExclude:
        """Create ListIncludeExclude from configuration model."""
        if text := m.text.strip():
            text_list = convert_string_to_list(text)
            patterns = tuple(re.compile(re_fmt.format(re.escape(i)), re.IGNORECASE) for i in text_list)
        else:
            patterns = ()
        return ListIncludeExclude(
            is_enabled=m.is_enabled and bool(text),
            is_valid=(
                (lambda part: any(p.search(part) for p in patterns))
                if m.should_include
                else (lambda part: not any(p.search(part) for p in patterns))
            ),
        )


@dataclass(slots=True)
class MinMax:
    """Dataclass for min-max limit configuration."""

    is_enabled: bool
    is_valid: Callable[[float], bool]

    @classmethod
    def from_model(cls, m: MinMaxModel, mapping: dict[str, float]) -> MinMax:
        """Create MinMax from configuration model."""
        minimum = m.minimum * mapping.get(m.unit, 1.0)
        maximum = m.maximum * mapping.get(m.unit, 1.0)
        return cls(
            is_enabled=m.is_enabled,
            is_valid=lambda val: minimum <= val <= maximum,
        )
