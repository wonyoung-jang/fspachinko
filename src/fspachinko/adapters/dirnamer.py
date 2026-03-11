"""Builder module for core functionality."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from os.path import join


@dataclass(slots=True)
class AbstractDirectoryNamer(ABC):
    """Class for determining the destination folder name based on the configuration."""

    @abstractmethod
    def gen_dir_name(self) -> str:
        """Return the destination folder name."""


@dataclass(slots=True)
class UniqueDirectoryNamer(AbstractDirectoryNamer):
    """Directory namer that generates unique folder names."""

    dest: str
    name: str

    def gen_dir_name(self) -> str:
        """Return a unique destination folder name."""
        return join(self.dest, self.name)


@dataclass(slots=True)
class StaticDirectoryNamer(AbstractDirectoryNamer):
    """Directory namer that returns a static folder name."""

    dest: str

    def gen_dir_name(self) -> str:
        """Return the static destination folder name."""
        return self.dest
