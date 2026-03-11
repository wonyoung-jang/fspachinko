"""File count module."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from random import randint


@dataclass(slots=True)
class AbstractFileCounter(ABC):
    """Class for generating file counts based on configuration."""

    @abstractmethod
    def gen_file_count(self) -> int:
        """Generate a file count."""


@dataclass(slots=True)
class StaticFileCounter(AbstractFileCounter):
    """Generates a fixed file count."""

    count: int

    def gen_file_count(self) -> int:
        """Return the fixed file count."""
        return self.count


@dataclass(slots=True)
class RandomFileCounter(AbstractFileCounter):
    """Generates a random file count within a specified range."""

    rand_min: int
    rand_max: int

    def gen_file_count(self) -> int:
        """Return a random file count within the specified range."""
        return randint(self.rand_min, self.rand_max)
