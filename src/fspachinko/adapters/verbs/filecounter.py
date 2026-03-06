"""File count module."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from random import randint
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...config import FilecountModel


def get_filecount_fn(m: FilecountModel) -> AbstractFileCounter:
    """Return a function that determines the number of files to transfer based on the configuration."""
    match m.is_rand_enabled:
        case True:
            return RandomFileCounter(rand_min=m.rand_min, rand_max=m.rand_max)
        case False:
            return StaticFileCounter(count=m.count)


@dataclass(slots=True)
class AbstractFileCounter(ABC):
    """Class for generating file counts based on configuration."""

    @abstractmethod
    def __call__(self) -> int:
        """Generate a file count."""


@dataclass(slots=True)
class StaticFileCounter(AbstractFileCounter):
    """Generates a fixed file count."""

    count: int

    def __call__(self) -> int:
        """Return the fixed file count."""
        return self.count


@dataclass(slots=True)
class RandomFileCounter(AbstractFileCounter):
    """Generates a random file count within a specified range."""

    rand_min: int
    rand_max: int

    def __call__(self) -> int:
        """Return a random file count within the specified range."""
        return randint(self.rand_min, self.rand_max)
