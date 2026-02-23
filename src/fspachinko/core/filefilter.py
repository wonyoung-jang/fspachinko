"""Config validation functions."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .config import get_inc_exc_filter_fn, get_min_max_filter_fn
from .constants import SIZE_MAP, TIME_MAP, ReStrFmt
from .helpers import get_duration

if TYPE_CHECKING:
    from collections.abc import Callable

    from .config import ConfigModel
    from .walker import FSEntry


@dataclass(slots=True)
class FileFilter:
    """Class for validating files based on filter configuration."""

    filters: tuple[Filter, ...]

    @classmethod
    def from_model(cls, m: ConfigModel) -> FileFilter:
        """Create a FileFilter instance from the configuration model."""
        fmap: list[tuple[type[Filter], Callable[[Any], bool] | None]] = [
            (DirnameFilter, get_inc_exc_filter_fn(m.directory_name, re_fmt=ReStrFmt.DIRECTORY)),
            (KeywordFilter, get_inc_exc_filter_fn(m.keyword, re_fmt=ReStrFmt.KEYWORD)),
            (ExtensionFilter, get_inc_exc_filter_fn(m.extension, re_fmt=ReStrFmt.EXTENSION)),
            (FilesizeFilter, get_min_max_filter_fn(m.filesize, mapping=SIZE_MAP)),
            (DurationFilter, get_min_max_filter_fn(m.duration, mapping=TIME_MAP)),
        ]
        filters = (filter_c(is_valid=fn) for filter_c, fn in fmap if fn is not None)
        return cls(filters=tuple(filters))

    def __call__(self, entry: FSEntry) -> bool:
        """Check if a file is valid based on the current filters."""
        if not self.filters:
            return True
        return all(f(entry) for f in self.filters)


@dataclass(slots=True)
class Filter(ABC):
    """Class for filtering files based on filter configuration."""

    is_valid: Callable[[str | float], bool]

    @abstractmethod
    def __call__(self, entry: FSEntry) -> bool:
        """Check if a file is valid based on the current filter."""


@dataclass(slots=True)
class DirnameFilter(Filter):
    """Filter for parent directory names."""

    def __call__(self, entry: FSEntry) -> bool:
        """Filter the parent directory name."""
        return self.is_valid(entry.parent)


@dataclass(slots=True)
class KeywordFilter(Filter):
    """Filter for filename keywords."""

    def __call__(self, entry: FSEntry) -> bool:
        """Filter the filename stem against keywords."""
        return self.is_valid(entry.stem)


@dataclass(slots=True)
class ExtensionFilter(Filter):
    """Filter for file extensions."""

    def __call__(self, entry: FSEntry) -> bool:
        """Filter the file extension."""
        return self.is_valid(entry.ext)


@dataclass(slots=True)
class FilesizeFilter(Filter):
    """Filter for file size."""

    def __call__(self, entry: FSEntry) -> bool:
        """Filter the file size."""
        return self.is_valid(entry.size)


@dataclass(slots=True)
class DurationFilter(Filter):
    """Filter for file duration."""

    def __call__(self, entry: FSEntry) -> bool:
        """Filter the file duration."""
        return self.is_valid(get_duration(entry.path))
