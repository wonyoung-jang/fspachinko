"""Config validation functions."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import RangeFilterModel


def get_rangefilter_fn(m: RangeFilterModel, mapping: dict[str, float]) -> RangeFilterFn | None:
    """Create a range filter function from it's configuration model."""
    if m.is_enabled:
        minimum = m.minimum * mapping.get(m.unit, 1.0)
        maximum = m.maximum * mapping.get(m.unit, 1.0)
        is_valid_min = minimum >= 0
        is_valid_max = maximum < float("inf")
        if is_valid_min and is_valid_max:
            return RangeMinMaxFilterFn(minimum=minimum, maximum=maximum)
        if is_valid_min:
            return RangeMinFilterFn(minimum=minimum)
        if is_valid_max:
            return RangeMaxFilterFn(maximum=maximum)
    return None


@dataclass(slots=True)
class RangeFilterFn(ABC):
    """Class for filtering files based on a minimum and maximum value."""

    @abstractmethod
    def __call__(self, val: float) -> bool:
        """Check if a value is within the minimum and maximum range."""


@dataclass(slots=True)
class RangeMinMaxFilterFn(RangeFilterFn):
    """Class for filtering files based on a minimum and maximum value."""

    minimum: float
    maximum: float

    def __call__(self, val: float) -> bool:
        """Check if a value is within the minimum and maximum range."""
        return self.minimum <= val <= self.maximum


@dataclass(slots=True)
class RangeMinFilterFn(RangeFilterFn):
    """Class for filtering files based on a minimum value."""

    minimum: float

    def __call__(self, val: float) -> bool:
        """Check if a value is greater than or equal to the minimum."""
        return val >= self.minimum


@dataclass(slots=True)
class RangeMaxFilterFn(RangeFilterFn):
    """Class for filtering files based on a maximum value."""

    maximum: float

    def __call__(self, val: float) -> bool:
        """Check if a value is less than or equal to the maximum."""
        return val <= self.maximum
