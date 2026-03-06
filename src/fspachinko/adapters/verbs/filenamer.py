"""Module for file naming based on template configuration."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from os.path import basename, split
from typing import TYPE_CHECKING

from ...constants import INVALID_FILENAME_CHARS, FilenameTemplate, FilenameTemplateMapKey

if TYPE_CHECKING:
    from ...config import FilenameModel
    from ...domain.model import FSEntry


def get_filenamer_fn(m: FilenameModel) -> AbstractFilenamer:
    """Return a function that determines the destination file name based on the configuration."""
    match not m.is_enabled or m.template == FilenameTemplate.ORIGINAL:
        case True:
            return StaticFilenamer()
        case False:
            return TemplateFilenamer(m.template)


@dataclass(slots=True)
class AbstractFilenamer(ABC):
    """Abstract class for file naming."""

    @abstractmethod
    def __call__(self, entry: FSEntry, count: int) -> str:
        """Calculate the destination file stem based on template configuration."""


@dataclass(slots=True)
class StaticFilenamer(AbstractFilenamer):
    """Filenamer that returns the original file name."""

    def __call__(self, entry: FSEntry, count: int) -> str:
        """Return the original file name."""
        return entry.stem


@dataclass(slots=True)
class TemplateFilenamer(AbstractFilenamer):
    """Dataclass for file naming."""

    template: str

    def __call__(self, entry: FSEntry, count: int) -> str:
        """Calculate the destination file stem based on template configuration."""
        mapping = self.SafeDict(
            {
                FilenameTemplateMapKey.INDEX: count + 1,
                FilenameTemplateMapKey.ORIGINAL: entry.stem,
                FilenameTemplateMapKey.PARENT: basename(entry.parent),
                FilenameTemplateMapKey.PARENTS_TO_ROOT: split(entry.path)[0],
            }
        )
        try:
            formatted_stem = self.template.format_map(mapping)
            return "".join(c for c in formatted_stem if c not in INVALID_FILENAME_CHARS)
        except KeyError, ValueError:
            return entry.stem

    class SafeDict(dict):
        """A helper class for string formatting.

        If a key is missing, it returns the key wrapped in braces
        instead of raising a KeyError.
        """

        def __missing__(self, key: str) -> str:
            """Return the key wrapped in braces if missing."""
            return "{" + key + "}"
