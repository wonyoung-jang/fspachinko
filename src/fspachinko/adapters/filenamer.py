"""Module for file naming based on template configuration."""

from os.path import basename, split
from typing import TYPE_CHECKING

from ..constants import INVALID_FILENAME_CHARS, FilenameTemplateMapKey

if TYPE_CHECKING:
    from ..domain.model import FSEntry


def get_name_from_template(entry: FSEntry, count: int, template: str) -> str:
    """Calculate the destination file stem based on template configuration."""
    mapping = SafeDict(
        {
            FilenameTemplateMapKey.INDEX: count + 1,
            FilenameTemplateMapKey.ORIGINAL: entry.stem,
            FilenameTemplateMapKey.PARENT: basename(entry.parent),
            FilenameTemplateMapKey.PARENTS_TO_ROOT: split(entry.path)[0],
        }
    )
    try:
        formatted_stem = template.format_map(mapping)
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
