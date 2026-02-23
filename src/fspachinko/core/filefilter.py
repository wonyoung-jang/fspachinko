"""Config validation functions."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .constants import SIZE_MAP, TIME_MAP, ReStrFmt
from .filterrange import RangeFilterFn, get_rangefilter_fn
from .filtertext import TextFilterFn, get_textfilter_fn
from .helpers import get_duration

if TYPE_CHECKING:
    from .config import ConfigModel
    from .walker import FSEntry


@dataclass(slots=True)
class FileFilter:
    """Class for validating files based on filter configuration."""

    filters: tuple[Filter, ...]

    @classmethod
    def from_model(cls, m: ConfigModel) -> FileFilter:
        """Create a FileFilter instance from the configuration model."""
        fmap: list[tuple[type[Filter], TextFilterFn | RangeFilterFn | None]] = [
            (DirnameFilter, get_textfilter_fn(m.directory_name, re_fmt=ReStrFmt.DIRECTORY)),
            (KeywordFilter, get_textfilter_fn(m.keyword, re_fmt=ReStrFmt.KEYWORD)),
            (ExtensionFilter, get_textfilter_fn(m.extension, re_fmt=ReStrFmt.EXTENSION)),
            (FilesizeFilter, get_rangefilter_fn(m.filesize, mapping=SIZE_MAP)),
            (DurationFilter, get_rangefilter_fn(m.duration, mapping=TIME_MAP)),
        ]
        filters = (filter_c(call=fn) for filter_c, fn in fmap if fn is not None)
        return cls(filters=tuple(filters))

    def __call__(self, entry: FSEntry) -> bool:
        """Check if a file is valid based on the current filters."""
        if self.filters:
            return all(f(entry) for f in self.filters)
        return True


@dataclass(slots=True)
class Filter(ABC):
    """Class for filtering files based on filter configuration."""

    call: TextFilterFn | RangeFilterFn

    @abstractmethod
    def __call__(self, entry: FSEntry) -> bool:
        """Check if a file is valid based on the current filter."""


@dataclass(slots=True)
class TextFilter(Filter):
    """Filter for text-based criteria."""

    call: TextFilterFn


@dataclass(slots=True)
class DirnameFilter(TextFilter):
    """Filter for parent directory names."""

    def __call__(self, entry: FSEntry) -> bool:
        """Filter the parent directory name."""
        return self.call(entry.parent)


@dataclass(slots=True)
class KeywordFilter(TextFilter):
    """Filter for filename keywords."""

    def __call__(self, entry: FSEntry) -> bool:
        """Filter the filename stem against keywords."""
        return self.call(entry.stem)


@dataclass(slots=True)
class ExtensionFilter(TextFilter):
    """Filter for file extensions."""

    def __call__(self, entry: FSEntry) -> bool:
        """Filter the file extension."""
        return self.call(entry.ext)


@dataclass(slots=True)
class RangeFilter(Filter):
    """Filter for file size."""

    call: RangeFilterFn


@dataclass(slots=True)
class FilesizeFilter(RangeFilter):
    """Filter for file size."""

    def __call__(self, entry: FSEntry) -> bool:
        """Filter the file size."""
        return self.call(entry.size)


@dataclass(slots=True)
class DurationFilter(RangeFilter):
    """Filter for file duration."""

    def __call__(self, entry: FSEntry) -> bool:
        """Filter the file duration."""
        return self.call(get_duration(entry.path))
