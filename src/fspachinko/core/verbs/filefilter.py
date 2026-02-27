"""Config validation functions."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..constants import SIZE_MAP, TIME_MAP, ReStrFmt
from ..helpers import get_duration
from .filterrange import RangeFilterFn, get_rangefilter_fn
from .filtertext import TextFilterFn, get_textfilter_fn

if TYPE_CHECKING:
    from ..config import ConfigModel
    from ..model import FSEntry


def get_filefilter_fn(m: ConfigModel) -> AbstractFileFilter:
    """Create a FileFilter instance from the configuration model."""
    fmap: list[tuple[type[Filter], TextFilterFn | RangeFilterFn | None]] = [
        (DirnameFilter, get_textfilter_fn(m.dirname, re_fmt=ReStrFmt.DIRECTORY)),
        (KeywordFilter, get_textfilter_fn(m.keyword, re_fmt=ReStrFmt.KEYWORD)),
        (ExtensionFilter, get_textfilter_fn(m.extension, re_fmt=ReStrFmt.EXTENSION)),
        (FilesizeFilter, get_rangefilter_fn(m.filesize, mapping=SIZE_MAP)),
        (DurationFilter, get_rangefilter_fn(m.duration, mapping=TIME_MAP)),
    ]
    filters = tuple(filter_c(call=fn) for filter_c, fn in fmap if fn is not None)
    if filters:
        if len(filters) == 1:
            return SingularFileFilter(filter=filters[0])
        return CompositeFileFilter(filters=filters)
    return NoOpFileFilter()


class AbstractFileFilter(ABC):
    """Abstract class for validating files based on filter configuration."""

    @abstractmethod
    def __call__(self, e: FSEntry) -> bool:
        """Check if a file is valid based on the current filters."""


@dataclass(slots=True)
class NoOpFileFilter(AbstractFileFilter):
    """Class for validating files based on filter configuration."""

    def __call__(self, e: FSEntry) -> bool:
        """Check if a file is valid based on the current filters."""
        return True


@dataclass(slots=True)
class SingularFileFilter(AbstractFileFilter):
    """Class for validating files based on a single enabled filter."""

    filter: Filter

    def __call__(self, e: FSEntry) -> bool:
        """Check if a file is valid based on the current filters."""
        return self.filter(e)


@dataclass(slots=True)
class CompositeFileFilter(AbstractFileFilter):
    """Class for validating files based on multiple enabled filters."""

    filters: tuple[Filter, ...]

    def __call__(self, e: FSEntry) -> bool:
        """Check if a file is valid based on the current filters."""
        return all(f(e) for f in self.filters)


# Individual filter classes


@dataclass(slots=True)
class Filter(ABC):
    """Class for filtering files based on filter configuration."""

    call: TextFilterFn | RangeFilterFn

    @abstractmethod
    def __call__(self, e: FSEntry) -> bool:
        """Check if a file is valid based on the current filter."""


@dataclass(slots=True)
class TextFilter(Filter):
    """Filter for text-based criteria."""

    call: TextFilterFn


@dataclass(slots=True)
class DirnameFilter(TextFilter):
    """Filter for parent directory names."""

    def __call__(self, e: FSEntry) -> bool:
        """Filter the parent directory name."""
        return self.call(e.parent)


@dataclass(slots=True)
class KeywordFilter(TextFilter):
    """Filter for filename keywords."""

    def __call__(self, e: FSEntry) -> bool:
        """Filter the filename stem against keywords."""
        return self.call(e.stem)


@dataclass(slots=True)
class ExtensionFilter(TextFilter):
    """Filter for file extensions."""

    def __call__(self, e: FSEntry) -> bool:
        """Filter the file extension."""
        return self.call(e.ext)


@dataclass(slots=True)
class RangeFilter(Filter):
    """Filter for file size."""

    call: RangeFilterFn


@dataclass(slots=True)
class FilesizeFilter(RangeFilter):
    """Filter for file size."""

    def __call__(self, e: FSEntry) -> bool:
        """Filter the file size."""
        return self.call(e.size)


@dataclass(slots=True)
class DurationFilter(RangeFilter):
    """Filter for file duration."""

    def __call__(self, e: FSEntry) -> bool:
        """Filter the file duration."""
        return self.call(get_duration(e.path))
