"""Config validation functions."""

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..constants import SIZE_MAP, TIME_MAP, ReStrFmt
from .media import get_duration

if TYPE_CHECKING:
    from ..config import ConfigModel, RangeFilterModel, TextFilterModel
    from ..domain.model import FSEntry

logger = logging.getLogger(__name__)


def get_filefilter_fn(m: ConfigModel) -> AbstractFileFilter:
    """Create a FileFilter instance from the configuration model."""
    fmap: dict[type[Filter], TextFilterFn | RangeFilterFn | None] = {
        DirnameFilter: get_textfilter_fn(m.dirname, re_fmt=ReStrFmt.DIRECTORY),
        KeywordFilter: get_textfilter_fn(m.keyword, re_fmt=ReStrFmt.KEYWORD),
        ExtensionFilter: get_textfilter_fn(m.extension, re_fmt=ReStrFmt.EXTENSION),
        FilesizeFilter: get_rangefilter_fn(m.filesize, mapping=SIZE_MAP),
        DurationFilter: get_rangefilter_fn(m.duration, mapping=TIME_MAP),
    }
    filters = tuple(filter_c(call=fn) for filter_c, fn in fmap.items() if fn is not None)

    match len(filters) > 0, len(filters) == 1:
        case True, True:
            return SingularFileFilter(filter=filters[0])
        case True, False:
            return CompositeFileFilter(filters=filters)
        case _:
            return NoOpFileFilter()


# The aggregate filter classes


@dataclass(slots=True)
class AbstractFileFilter(ABC):
    """Abstract class for validating files based on filter configuration."""

    @abstractmethod
    def is_valid(self, e: FSEntry) -> bool:
        """Check if a file is valid based on the current filters."""


@dataclass(slots=True)
class NoOpFileFilter(AbstractFileFilter):
    """Class for validating files based on filter configuration."""

    def is_valid(self, e: FSEntry) -> bool:
        """Check if a file is valid based on the current filters."""
        return True


@dataclass(slots=True)
class SingularFileFilter(AbstractFileFilter):
    """Class for validating files based on a single enabled filter."""

    filter: Filter

    def is_valid(self, e: FSEntry) -> bool:
        """Check if a file is valid based on the current filters."""
        return self.filter.is_valid(e)


@dataclass(slots=True)
class CompositeFileFilter(AbstractFileFilter):
    """Class for validating files based on multiple enabled filters."""

    filters: tuple[Filter, ...]

    def is_valid(self, e: FSEntry) -> bool:
        """Check if a file is valid based on the current filters."""
        return all(f.is_valid(e) for f in self.filters)


# Individualized filter classes


@dataclass(slots=True)
class Filter(ABC):
    """Class for filtering files based on filter configuration."""

    call: TextFilterFn | RangeFilterFn

    @abstractmethod
    def is_valid(self, e: FSEntry) -> bool:
        """Check if a file is valid based on the current filter."""


@dataclass(slots=True)
class TextFilter(Filter):
    """Filter for text-based criteria."""

    call: TextFilterFn


@dataclass(slots=True)
class DirnameFilter(TextFilter):
    """Filter for parent directory names."""

    def is_valid(self, e: FSEntry) -> bool:
        """Filter the parent directory name."""
        return self.call.is_valid(e.parent)


@dataclass(slots=True)
class KeywordFilter(TextFilter):
    """Filter for filename keywords."""

    def is_valid(self, e: FSEntry) -> bool:
        """Filter the filename stem against keywords."""
        return self.call.is_valid(e.stem)


@dataclass(slots=True)
class ExtensionFilter(TextFilter):
    """Filter for file extensions."""

    def is_valid(self, e: FSEntry) -> bool:
        """Filter the file extension."""
        return self.call.is_valid(e.ext)


@dataclass(slots=True)
class RangeFilter(Filter):
    """Filter for file size."""

    call: RangeFilterFn


@dataclass(slots=True)
class FilesizeFilter(RangeFilter):
    """Filter for file size."""

    def is_valid(self, e: FSEntry) -> bool:
        """Filter the file size."""
        return self.call.is_valid(e.size)


@dataclass(slots=True)
class DurationFilter(RangeFilter):
    """Filter for file duration."""

    def is_valid(self, e: FSEntry) -> bool:
        """Filter the file duration."""
        return self.call.is_valid(get_duration(e.path))


# Text based filter classes


def get_textfilter_fn(m: TextFilterModel, re_fmt: str) -> TextFilterFn | None:
    """Create an include-exclude filter function from configuration model."""
    if not (m.is_enabled and m.text):
        return None

    split_text = set(m.text.split(","))
    patterns = tuple(re.compile(re_fmt.format(re.escape(t)), re.IGNORECASE) for t in split_text)

    match m.should_include, len(patterns) == 1:
        case (True, True):
            return IncludeTextFilterSingular(pattern=patterns[0])
        case (True, False):
            return IncludeTextFilter(patterns=patterns)
        case (False, True):
            return ExcludeTextFilterSingular(pattern=patterns[0])
        case (False, False):
            return ExcludeTextFilter(patterns=patterns)


@dataclass(slots=True)
class TextFilterFn(ABC):
    """Class for filtering files based on text criteria."""

    @abstractmethod
    def is_valid(self, part: str) -> bool:
        """Filter based on text criteria."""


@dataclass(slots=True)
class MultipleTextFilterFn(TextFilterFn):
    """Multiple filter for text criteria."""

    patterns: tuple[re.Pattern, ...]


@dataclass(slots=True)
class IncludeTextFilter(MultipleTextFilterFn):
    """Include filter for text criteria."""

    def is_valid(self, part: str) -> bool:
        """Return True if any pattern matches the text part."""
        return any(p.search(part) for p in self.patterns)


@dataclass(slots=True)
class ExcludeTextFilter(MultipleTextFilterFn):
    """Exclude filter for text criteria."""

    def is_valid(self, part: str) -> bool:
        """Return True if no patterns match the text part."""
        return not any(p.search(part) for p in self.patterns)


@dataclass(slots=True)
class SingularTextFilterFn(TextFilterFn):
    """Singular filter for text criteria."""

    pattern: re.Pattern


@dataclass(slots=True)
class IncludeTextFilterSingular(SingularTextFilterFn):
    """Include filter for a single text criteria."""

    def is_valid(self, part: str) -> bool:
        """Return True if the pattern matches the text part."""
        return self.pattern.search(part) is not None


@dataclass(slots=True)
class ExcludeTextFilterSingular(SingularTextFilterFn):
    """Exclude filter for a single text criteria."""

    def is_valid(self, part: str) -> bool:
        """Return True if the pattern does not match the text part."""
        return self.pattern.search(part) is None


# Range based filter classes


def get_rangefilter_fn(m: RangeFilterModel, mapping: dict[str, int | float]) -> RangeFilterFn | None:
    """Create a range filter function from it's configuration model."""
    if not m.is_enabled:
        return None

    minimum = m.minimum * mapping.get(m.unit, 1.0)
    maximum = m.maximum * mapping.get(m.unit, 1.0)

    match minimum >= 0, maximum < float("inf"):
        case (True, True):
            return RangeMinMaxFilterFn(minimum=minimum, maximum=maximum)
        case (True, False):
            return RangeMinFilterFn(minimum=minimum)
        case (False, True):
            return RangeMaxFilterFn(maximum=maximum)


@dataclass(slots=True)
class RangeFilterFn(ABC):
    """Class for filtering files based on a minimum and maximum value."""

    @abstractmethod
    def is_valid(self, val: float) -> bool:
        """Check if a value is within the minimum and maximum range."""


@dataclass(slots=True)
class RangeMinMaxFilterFn(RangeFilterFn):
    """Class for filtering files based on a minimum and maximum value."""

    minimum: float
    maximum: float

    def is_valid(self, val: float) -> bool:
        """Check if a value is within the minimum and maximum range."""
        return self.minimum <= val <= self.maximum


@dataclass(slots=True)
class RangeMinFilterFn(RangeFilterFn):
    """Class for filtering files based on a minimum value."""

    minimum: float

    def is_valid(self, val: float) -> bool:
        """Check if a value is greater than or equal to the minimum."""
        return val >= self.minimum


@dataclass(slots=True)
class RangeMaxFilterFn(RangeFilterFn):
    """Class for filtering files based on a maximum value."""

    maximum: float

    def is_valid(self, val: float) -> bool:
        """Check if a value is less than or equal to the maximum."""
        return val <= self.maximum
