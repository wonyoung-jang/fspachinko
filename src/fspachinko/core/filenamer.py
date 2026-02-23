"""Module for file naming based on template configuration."""

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .constants import FilenameTemplateMapKey
from .helpers import SafeDict, get_valid_filename_from_str

if TYPE_CHECKING:
    from .config import FilenameModel
    from .context import DateTimeStamp
    from .engine import JobRequest
    from .walker import FSEntry


@dataclass(slots=True)
class Filenamer:
    """Dataclass for file naming."""

    is_enabled: bool
    template: str

    @classmethod
    def from_model(cls, m: FilenameModel) -> Filenamer:
        """Create Filename from configuration model."""
        return cls(is_enabled=m.is_enabled, template=m.template)

    def __call__(self, entry: FSEntry, request: JobRequest, dtstamp: DateTimeStamp) -> str:
        """Calculate the destination file stem based on template configuration."""
        if not self.is_enabled:
            return entry.stem

        stem = entry.stem
        mapping = SafeDict(
            {
                FilenameTemplateMapKey.ORIGINAL: stem,
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
            return stem
