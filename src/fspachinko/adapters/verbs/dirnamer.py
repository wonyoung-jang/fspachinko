"""Builder module for core functionality."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from os.path import join
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...config import DirectoryModel


def get_dirname_fn(m: DirectoryModel, dest: str) -> AbstractDirectoryNamer:
    """Return a function that determines the destination folder name based on the configuration."""
    match m.is_enabled:
        case True:
            return UniqueDirectoryNamer(dest=dest, name=m.name)
        case False:
            return StaticDirectoryNamer(dest=dest)


@dataclass(slots=True)
class AbstractDirectoryNamer(ABC):
    """Class for determining the destination folder name based on the configuration."""

    @abstractmethod
    def __call__(self) -> str:
        """Return the destination folder name."""


@dataclass(slots=True)
class UniqueDirectoryNamer(AbstractDirectoryNamer):
    """Directory namer that generates unique folder names."""

    dest: str
    name: str

    def __call__(self) -> str:
        """Return a unique destination folder name."""
        return join(self.dest, self.name)


@dataclass(slots=True)
class StaticDirectoryNamer(AbstractDirectoryNamer):
    """Directory namer that returns a static folder name."""

    dest: str

    def __call__(self) -> str:
        """Return the static destination folder name."""
        return self.dest
