"""Config validation functions."""

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..utils import get_duration

if TYPE_CHECKING:
    import os
    from collections.abc import Callable

    from ..config import ListIncludeExclude, MinMax
    from .walker import FSEntry

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class FileValidator:
    """Class for validating files based on configuration."""

    keywords: ListIncludeExclude
    extensions: ListIncludeExclude
    filesize: MinMax
    duration: MinMax
    validators: tuple[Callable, ...] = ()

    def __post_init__(self) -> None:
        """Gather validation functions based on enabled filters."""
        self._gather_validators()

    def is_valid(self, entry: FSEntry) -> bool:
        """Check if a file is valid based on the current filters."""
        return all(is_valid(entry) for is_valid in self.validators)

    def _gather_validators(self) -> None:
        """Gather validation functions based on enabled filters."""
        v = []

        if self.filesize.is_enabled:
            v.append(self._is_valid_filesize)

        if self.extensions.is_enabled:
            v.append(self._is_valid_extension)

        if self.keywords.is_enabled:
            v.append(self._is_valid_keyword)

        self.validators = tuple(v)

    def _is_valid_filesize(self, entry: FSEntry) -> bool:
        """Check if a file is valid based on the current filters."""
        return self.filesize.is_valid(entry.size)

    def _is_valid_extension(self, entry: FSEntry) -> bool:
        """Check if a file is valid based on the current filters."""
        return self.extensions.is_valid(entry.ext)

    def _is_valid_keyword(self, entry: FSEntry) -> bool:
        """Check if a file is valid based on the current filters."""
        return self.keywords.is_valid(entry.stem)

    def is_valid_duration(self, entry: os.PathLike) -> bool:
        """Check if a file is valid based on the current filters."""
        if not self.duration.is_enabled:
            return True

        duration = get_duration(entry)
        return self.duration.is_valid(duration)
