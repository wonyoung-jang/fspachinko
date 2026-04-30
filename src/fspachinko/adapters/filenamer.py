"""Adapter for generating filenames based on templates."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from functools import cache
from os.path import basename, split
from typing import TYPE_CHECKING

from fspachinko.fp import Fp

if TYPE_CHECKING:
    from collections.abc import Callable

    from fspachinko.domain.model import FSEntry

FILENAME_TEMPLATE_MAP: dict[Fp.FilenameTemplate, Callable[[FSEntry, int], str | int]] = {
    Fp.FilenameTemplate.ORIGINAL: lambda e, _: e.stem,
    Fp.FilenameTemplate.INDEX: lambda _, c: c + 1,
    Fp.FilenameTemplate.PARENT: lambda e, _: basename(e.parent),
    Fp.FilenameTemplate.PARENTS_TO_ROOT: lambda e, _: split(e.path)[0],
}


@cache
def _available_filename_map(template: str) -> dict[str, Callable[[FSEntry, int], str | int]]:
    """Get the mapping of available filename template variables."""
    return {templ[1:-1]: fn for templ, fn in FILENAME_TEMPLATE_MAP.items() if templ in template}


@dataclass(slots=True)
class AbstractFilenamer(ABC):
    """Abstract filenamer."""

    template: str

    @abstractmethod
    def __call__(self, entry: FSEntry, count: int) -> str:
        """Generate a filename."""


@dataclass(slots=True)
class TemplateFilenamer(AbstractFilenamer):
    """Filenamer that generates filenames based on templates."""

    _map: dict[str, Callable[[FSEntry, int], str | int]] = field(init=False)

    def __post_init__(self) -> None:
        """Validate the template."""
        self.template = "".join(c for c in self.template if c not in Fp.INVALID_FILENAME_CHARS)
        self._map = _available_filename_map(self.template)

    def __call__(self, entry: FSEntry, count: int) -> str:
        """Generate a filename based on the specified template."""
        try:
            mapping = {templ: fn(entry, count) for templ, fn in self._map.items()}
            return self.template.format_map(mapping)
        except KeyError, ValueError, IndexError:
            return entry.stem
