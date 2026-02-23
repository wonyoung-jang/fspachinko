"""File count module."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from random import randint
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import FilecountModel


def get_filecount_fn(m: FilecountModel) -> FileCountGenerator:
    """Return a function that determines the number of files to transfer based on the configuration."""
    if m.is_rand_enabled:
        return RandomFileCount(rand_min=m.rand_min, rand_max=m.rand_max)
    return FixedFileCount(count=m.count)


class FileCountGenerator(ABC):
    """Class for generating file counts based on configuration."""

    @abstractmethod
    def __call__(self) -> int:
        """Generate a file count."""


@dataclass(slots=True)
class FixedFileCount(FileCountGenerator):
    """Generates a fixed file count."""

    count: int

    def __call__(self) -> int:
        """Return the fixed file count."""
        return self.count


@dataclass(slots=True)
class RandomFileCount(FileCountGenerator):
    """Generates a random file count within a specified range."""

    rand_min: int
    rand_max: int

    def __call__(self) -> int:
        """Return a random file count within the specified range."""
        return randint(self.rand_min, self.rand_max)
