"""Module for file naming based on template configuration."""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .constants import FilenameTemplate, FilenameTemplateMapKey
from .helpers import SafeDict, get_valid_filename_from_str

if TYPE_CHECKING:
    from .config import FilenameModel
    from .context import DateTimeStamp
    from .engine import JobRequest
    from .walker import FSEntry


def get_filenamer_fn(m: FilenameModel) -> Filenamer:
    """Return a function that determines the destination file name based on the configuration."""
    if not m.is_enabled:
        return StaticFilenamer()
    if m.template.strip() == FilenameTemplate.ORIGINAL:
        return StaticFilenamer()
    return TemplateFilenamer(m.template)


@dataclass(slots=True)
class Filenamer(ABC):
    """Abstract class for file naming."""

    @abstractmethod
    def __call__(self, entry: FSEntry, request: JobRequest, dtstamp: DateTimeStamp) -> str:
        """Calculate the destination file stem based on template configuration."""


@dataclass(slots=True)
class StaticFilenamer(Filenamer):
    """Filenamer that returns the original file name."""

    def __call__(self, entry: FSEntry, request: JobRequest, dtstamp: DateTimeStamp) -> str:
        """Return the original file name."""
        return entry.stem


@dataclass(slots=True)
class TemplateFilenamer(Filenamer):
    """Dataclass for file naming."""

    template: str

    def __call__(self, entry: FSEntry, request: JobRequest, dtstamp: DateTimeStamp) -> str:
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
