"""Builder module for core functionality."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .helpers import calc_unique_path_name

if TYPE_CHECKING:
    from .config import DirectoryModel


def get_dirname_fn(m: DirectoryModel, dest: str) -> DirectoryNamer:
    """Return a function that determines the destination folder name based on the configuration."""
    if m.is_enabled:
        return UniqueDirectoryNamer(name=m.name, dest=dest)
    return StaticDirectoryNamer(dest=dest)


class DirectoryNamer(ABC):
    """Class for determining the destination folder name based on the configuration."""

    @abstractmethod
    def __call__(self) -> str:
        """Return the destination folder name."""


@dataclass(slots=True)
class UniqueDirectoryNamer(DirectoryNamer):
    """Directory namer that generates unique folder names."""

    name: str
    dest: str

    def __call__(self) -> str:
        """Return a unique destination folder name."""
        return calc_unique_path_name(self.dest, self.name)


@dataclass(slots=True)
class StaticDirectoryNamer(DirectoryNamer):
    """Directory namer that returns a static folder name."""

    dest: str

    def __call__(self) -> str:
        """Return the static destination folder name."""
        return self.dest
