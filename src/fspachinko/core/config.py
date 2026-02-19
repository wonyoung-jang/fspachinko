"""Configuration dataclasses."""

import os
import re
from dataclasses import dataclass
from os.path import isabs, realpath
from random import randint
from typing import TYPE_CHECKING

from pydantic import BaseModel, field_validator

from .constants import FilenameTemplateMapKey, TransferMode
from .helpers import (
    SafeDict,
    calc_unique_path_name,
    convert_string_to_list,
    get_valid_filename_from_str,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from .context import DateTimeStamp
    from .engine import JobRequest
    from .walker import FSEntry


class FilecountModel(BaseModel):
    """Model for file count configuration."""

    count: int = 0
    is_rand_enabled: bool = False
    rand_min: int = 0
    rand_max: int = 0


class DirectoryModel(BaseModel):
    """Model for directory creation configuration."""

    is_enabled: bool = False
    name: str = ""
    count: int = 1


class FilenameModel(BaseModel):
    """Model for file renaming."""

    is_enabled: bool = False
    template: str = "{original}"


class IncludeExcludeFilterModel(BaseModel):
    """Model for list search filtering."""

    is_enabled: bool = True
    should_include: bool = True
    text: str = ""


class MinMaxFilterModel(BaseModel):
    """Model for range filter."""

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
    """Model for configuration."""

    root: str
    dest: str
    filecount: FilecountModel
    folder: DirectoryModel
    filename: FilenameModel
    directory_name: IncludeExcludeFilterModel
    keyword: IncludeExcludeFilterModel
    extension: IncludeExcludeFilterModel
    filesize: MinMaxFilterModel
    duration: MinMaxFilterModel
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
class Filenamer:
    """Dataclass for file naming."""

    template: str

    @classmethod
    def from_model(cls, m: FilenameModel) -> Filenamer:
        """Create Filename from configuration model."""
        return Filenamer(template=m.template)

    def __call__(self, entry: FSEntry, request: JobRequest, dtstamp: DateTimeStamp) -> str | None:
        """Calculate the destination file stem based on template configuration."""
        mapping = SafeDict(
            {
                FilenameTemplateMapKey.ORIGINAL: entry.stem,
                FilenameTemplateMapKey.DATE: dtstamp.date,
                FilenameTemplateMapKey.TIME: dtstamp.time,
                FilenameTemplateMapKey.DATETIME: dtstamp.date_time,
                FilenameTemplateMapKey.INDEX: request.file_count + 1,
                FilenameTemplateMapKey.PARENT: entry.parent,
                FilenameTemplateMapKey.PARENTS_TO_ROOT: "_".join(entry.path.split(os.sep)[:-1]),
            }
        )
        try:
            formatted_stem = self.template.format_map(mapping)
            return get_valid_filename_from_str(formatted_stem)
        except KeyError, ValueError:
            return entry.stem


def get_filecount_fn(m: FilecountModel) -> Callable[[], int]:
    """Return a function that determines the number of files to transfer based on the configuration."""
    return (lambda: randint(m.rand_min, m.rand_max)) if m.is_rand_enabled else (lambda: m.count)


def get_dirname_fn(m: DirectoryModel, dest: str) -> Callable[[], str]:
    """Return a function that determines the destination folder name based on the configuration."""
    return (lambda: calc_unique_path_name(dest, m.name)) if m.is_enabled else (lambda: dest)


def get_inc_exc_filter_fn(m: IncludeExcludeFilterModel, re_fmt: str) -> Callable[[str], bool] | None:
    """Create an include-exclude filter function from configuration model."""
    text = m.text.strip()
    if not (m.is_enabled and text):
        return None
    text_list = convert_string_to_list(text)
    patterns = tuple(re.compile(re_fmt.format(re.escape(i)), re.IGNORECASE) for i in text_list)
    return (
        (lambda part: any(p.search(part) for p in patterns))
        if m.should_include
        else (lambda part: not any(p.search(part) for p in patterns))
    )


def get_min_max_filter_fn(m: MinMaxFilterModel, mapping: dict[str, float]) -> Callable[[float], bool] | None:
    """Create a MinMax filter function from it's configuration model."""
    if not m.is_enabled:
        return None
    minimum = m.minimum * mapping.get(m.unit, 1.0)
    maximum = m.maximum * mapping.get(m.unit, 1.0)
    return lambda val: minimum <= val <= maximum
