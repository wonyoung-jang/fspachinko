"""Text Filter module."""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..config import TextFilterModel


def get_textfilter_fn(m: TextFilterModel, re_fmt: str) -> TextFilterFn | None:
    """Create an include-exclude filter function from configuration model."""
    if not (m.is_enabled and m.text):
        return None

    text = set(m.text.split(","))
    patterns = tuple(re.compile(re_fmt.format(re.escape(t)), re.IGNORECASE) for t in text)

    if m.should_include:
        if len(patterns) == 1:
            return IncludeTextFilterSingular(pattern=patterns[0])
        return IncludeTextFilter(patterns=patterns)

    if len(patterns) == 1:
        return ExcludeTextFilterSingular(pattern=patterns[0])
    return ExcludeTextFilter(patterns=patterns)


class TextFilterFn(ABC):
    """Class for filtering files based on text criteria."""

    @abstractmethod
    def __call__(self, part: str) -> bool:
        """Filter based on text criteria."""


@dataclass(slots=True)
class MultipleTextFilterFn(TextFilterFn):
    """Multiple filter for text criteria."""

    patterns: tuple[re.Pattern, ...]


@dataclass(slots=True)
class IncludeTextFilter(MultipleTextFilterFn):
    """Include filter for text criteria."""

    def __call__(self, part: str) -> bool:
        """Return True if any pattern matches the text part."""
        return any(p.search(part) for p in self.patterns)


@dataclass(slots=True)
class ExcludeTextFilter(MultipleTextFilterFn):
    """Exclude filter for text criteria."""

    def __call__(self, part: str) -> bool:
        """Return True if no patterns match the text part."""
        return not any(p.search(part) for p in self.patterns)


@dataclass(slots=True)
class SingularTextFilterFn(TextFilterFn):
    """Singular filter for text criteria."""

    pattern: re.Pattern


@dataclass(slots=True)
class IncludeTextFilterSingular(SingularTextFilterFn):
    """Include filter for a single text criteria."""

    def __call__(self, part: str) -> bool:
        """Return True if the pattern matches the text part."""
        return self.pattern.search(part) is not None


@dataclass(slots=True)
class ExcludeTextFilterSingular(SingularTextFilterFn):
    """Exclude filter for a single text criteria."""

    def __call__(self, part: str) -> bool:
        """Return True if the pattern does not match the text part."""
        return self.pattern.search(part) is None
