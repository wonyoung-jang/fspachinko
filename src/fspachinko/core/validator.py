"""Config validation functions."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .helpers import get_duration

if TYPE_CHECKING:
    from collections.abc import Callable

    from .config import ListIncludeExclude, MinMax
    from .walker import FSEntry


@dataclass(slots=True)
class FileValidatorBuilder:
    """Class for validating files based on configuration."""

    directory_name: ListIncludeExclude
    keywords: ListIncludeExclude
    extensions: ListIncludeExclude
    filesize: MinMax
    duration: MinMax

    def build(self) -> tuple[Callable[[FSEntry], bool], ...]:
        """Gather validation functions based on enabled filters."""
        vmap: tuple[tuple[bool, Callable[[FSEntry], bool]], ...] = (
            (self.directory_name.is_enabled, lambda e: self.directory_name.is_valid(e.parent)),
            (self.extensions.is_enabled, lambda e: self.extensions.is_valid(e.ext)),
            (self.keywords.is_enabled, lambda e: self.keywords.is_valid(e.stem)),
            (self.filesize.is_enabled, lambda e: self.filesize.is_valid(e.size)),
            (self.duration.is_enabled, lambda e: self.duration.is_valid(get_duration(e.path))),
        )
        return tuple(c for k, c in vmap if k)


@dataclass(slots=True)
class FileValidator:
    """Class for validating files based on configuration."""

    validators: tuple[Callable[[FSEntry], bool], ...]

    def is_valid(self, entry: FSEntry) -> bool:
        """Check if a file is valid based on the current filters."""
        return all(is_valid(entry) for is_valid in self.validators)
