"""Config validation functions."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .media import get_duration

if TYPE_CHECKING:
    import re

    from ..domain.model import FSEntry

logger = logging.getLogger(__name__)


#######################
## AGGREGATE FILTERS ##
#######################


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


########################
## INDIVIDUAL FILTERS ##
########################


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


##################
## TEXT FILTERS ##
##################


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


###################
## RANGE FILTERS ##
###################


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
