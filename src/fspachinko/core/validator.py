"""Config validation functions."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .helpers import get_duration

if TYPE_CHECKING:
    from collections.abc import Callable

    from .config import ListIncludeExclude, MinMax
    from .walker import FSEntry


@dataclass(slots=True)
class FileValidator:
    """Class for validating files based on configuration."""

    directory_name: ListIncludeExclude
    keywords: ListIncludeExclude
    extensions: ListIncludeExclude
    filesize: MinMax
    duration: MinMax
    validators: tuple[Callable, ...] = field(init=False)

    def __post_init__(self) -> None:
        """Gather validation functions based on enabled filters."""
        vmap = (
            (self.directory_name.is_enabled, self._is_valid_directory_name),
            (self.extensions.is_enabled, self._is_valid_extension),
            (self.keywords.is_enabled, self._is_valid_keyword),
            (self.filesize.is_enabled, self._is_valid_filesize),
            (self.duration.is_enabled, self._is_valid_duration),
        )
        self.validators = tuple([c for k, c in vmap if k])

    def is_valid(self, entry: FSEntry) -> bool:
        """Check if a file is valid based on the current filters."""
        return all(is_valid(entry) for is_valid in self.validators)

    def _is_valid_directory_name(self, entry: FSEntry) -> bool:
        """Check if a file is valid based on the current filters."""
        return self.directory_name.is_valid(entry.parent)

    def _is_valid_extension(self, entry: FSEntry) -> bool:
        """Check if a file is valid based on the current filters."""
        return self.extensions.is_valid(entry.ext)

    def _is_valid_keyword(self, entry: FSEntry) -> bool:
        """Check if a file is valid based on the current filters."""
        return self.keywords.is_valid(entry.stem)

    def _is_valid_filesize(self, entry: FSEntry) -> bool:
        """Check if a file is valid based on the current filters."""
        return self.filesize.is_valid(entry.size)

    def _is_valid_duration(self, entry: FSEntry) -> bool:
        """Check if a file is valid based on the current filters."""
        return self.duration.is_valid(get_duration(entry.path))
