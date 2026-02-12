"""Destination directory module."""

from dataclasses import dataclass
from os import mkdir
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass(slots=True)
class JobRequest:
    """Dataclass for job request."""

    target: int
    dest: str


@dataclass(slots=True)
class JobRequestFactory:
    """Factory for creating job requests."""

    get_file_count: Callable[[], int]
    determine_dest_dirname: Callable[[], str]
    dir_count: int

    def create(self) -> JobRequest:
        """Create a job request based on the current configuration."""
        dest = self.determine_dest_dirname()
        mkdir(dest)
        return JobRequest(target=self.get_file_count(), dest=dest)

    def generate(self) -> list[JobRequest]:
        """Generate multiple job requests."""
        return [self.create() for _ in range(self.dir_count)]
