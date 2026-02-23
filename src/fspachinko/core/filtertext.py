"""Text Filter module."""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .helpers import convert_string_to_tuple

if TYPE_CHECKING:
    from .config import IncludeExcludeFilterModel


def get_textfilter_fn(m: IncludeExcludeFilterModel, re_fmt: str) -> TextFilterFn | None:
    """Create an include-exclude filter function from configuration model."""
    text = m.text.strip()
    enabled = m.is_enabled and text
    if enabled:
        text_list = convert_string_to_tuple(text)
        patterns = tuple(re.compile(re_fmt.format(re.escape(i)), re.IGNORECASE) for i in text_list)
        if m.should_include:
            return IncludeTextFilter(patterns=patterns)
        return ExcludeTextFilter(patterns=patterns)
    return None


@dataclass(slots=True)
class TextFilterFn(ABC):
    """Class for filtering files based on text criteria."""

    patterns: tuple[re.Pattern, ...]

    @abstractmethod
    def __call__(self, part: str) -> bool:
        """Filter based on text criteria."""


@dataclass(slots=True)
class IncludeTextFilter(TextFilterFn):
    """Include filter for text criteria."""

    def __call__(self, part: str) -> bool:
        """Return True if any pattern matches the text part."""
        return any(p.search(part) for p in self.patterns)


@dataclass(slots=True)
class ExcludeTextFilter(TextFilterFn):
    """Exclude filter for text criteria."""

    def __call__(self, part: str) -> bool:
        """Return True if no patterns match the text part."""
        return not any(p.search(part) for p in self.patterns)
