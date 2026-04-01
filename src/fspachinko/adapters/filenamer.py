"""Adapter for generating filenames based on templates."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from os.path import basename, split
from typing import TYPE_CHECKING

from fspachinko.constants import FilenameTemplate

if TYPE_CHECKING:
    from collections.abc import Callable

    from fspachinko.domain.model import FSEntry

INVALID_FILENAME_CHARS: set[str] = set(r'\/:*?"<>|')
FILENAME_TEMPLATE_MAP: dict[FilenameTemplate, Callable[[FSEntry, int], str | int]] = {
    FilenameTemplate.ORIGINAL: lambda e, _: e.stem,
    FilenameTemplate.INDEX: lambda _, c: c + 1,
    FilenameTemplate.PARENT: lambda e, _: basename(e.parent),
    FilenameTemplate.PARENTS_TO_ROOT: lambda e, _: split(e.path)[0],
}


@dataclass(slots=True)
class AbstractFilenamer(ABC):
    """Abstract filenamer."""

    template: str = ""
    _map: dict[str, Callable[[FSEntry, int], str | int]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate the template."""
        self._map.update({t.strip("{}"): v for t, v in FILENAME_TEMPLATE_MAP.items() if t in self.template})

    @abstractmethod
    def __call__(self, entry: FSEntry, count: int) -> str:
        """Generate a filename."""


@dataclass(slots=True)
class TemplateFilenamer(AbstractFilenamer):
    """Filenamer that generates filenames based on templates."""

    def __call__(self, entry: FSEntry, count: int) -> str:
        """Generate a filename based on the specified template."""
        mapping = {t: v(entry, count) for t, v in self._map.items()}
        try:
            return "".join(c for c in self.template.format_map(mapping) if c not in INVALID_FILENAME_CHARS)
        except KeyError, ValueError, IndexError:
            return entry.stem
