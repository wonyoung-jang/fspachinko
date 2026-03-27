"""Translate the configuration model into commands."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .constants import SIZE_MAP, TIME_MAP, FilterName, ReStrFmt

if TYPE_CHECKING:
    from collections.abc import Callable

    from .configuration.model import ConfigModel
    from .domain.model import FSEntry


@dataclass(slots=True)
class ConfigToFileFilter:
    """Bootstrapper for translating configuration into a file filter function."""

    get_text_patterns: Callable
    get_duration: Callable

    def __call__(self, c: ConfigModel) -> Callable:
        """Translate the configuration into a file filter function."""
        filters = {}
        text_specs = [
            (c.dirname, FilterName.DIRNAME, ReStrFmt.DIRECTORY),
            (c.keyword, FilterName.KEYWORD, ReStrFmt.KEYWORD),
            (c.extension, FilterName.EXTENSION, ReStrFmt.EXTENSION),
        ]
        for model, name, re_fmt in text_specs:
            filters[name] = self.create_text_filter(
                text=model.text,
                re_fmt=re_fmt,
                is_enabled=model.is_enabled,
                should_include=model.should_include,
            )
        range_specs = [
            (c.filesize, FilterName.FILESIZE, SIZE_MAP),
            (c.duration, FilterName.DURATION, TIME_MAP),
        ]
        for model, name, unit_map in range_specs:
            mul = unit_map.get(model.unit, 1.0)
            filters[name] = self.create_range_filter(
                minimum=model.minimum * mul,
                maximum=model.maximum * mul,
                is_enabled=model.is_enabled,
            )
        filter_fns = tuple(self.create_filter(name, fn) for name, fn in filters.items() if fn)
        match len(filter_fns):
            case 0:
                return lambda _: True
            case 1:
                return filter_fns[0]
            case _:
                return lambda e: all(f(e) for f in filter_fns)

    def create_filter(self, name: str, fn: Callable) -> Any:
        """Create a filter function by name."""
        filter_mapping: dict[str, Callable[[FSEntry, Callable], bool]] = {
            FilterName.DIRNAME: lambda e, fn: fn(e.parent),
            FilterName.KEYWORD: lambda e, fn: fn(e.stem),
            FilterName.EXTENSION: lambda e, fn: fn(e.ext),
            FilterName.FILESIZE: lambda e, fn: fn(e.size),
            FilterName.DURATION: lambda e, fn: fn(self.get_duration(e.path)),
        }
        if filter_fn := filter_mapping.get(name):
            return lambda e, fn=fn: filter_fn(e, fn)
        msg = f"Invalid filter name: {name}"
        raise ValueError(msg)

    def create_text_filter(self, text: str, re_fmt: str, *, is_enabled: bool, should_include: bool) -> Any:
        """Create a text filter function."""
        if not (is_enabled and text):
            return None
        patterns = self.get_text_patterns(text, re_fmt)
        match len(patterns), should_include:
            case 1, True:
                return lambda p: patterns[0].search(p) is not None
            case 1, False:
                return lambda p: patterns[0].search(p) is None
            case _, True:
                return lambda p: any(ptn.search(p) for ptn in patterns)
            case _, False:
                return lambda p: not any(ptn.search(p) for ptn in patterns)

    def create_range_filter(self, minimum: float, maximum: float, *, is_enabled: bool) -> Any:
        """Create a range filter function."""
        if not is_enabled:
            return None
        match minimum >= 0, maximum < float("inf"):
            case True, True:
                return lambda v: minimum <= v <= maximum
            case True, False:
                return lambda v: v >= minimum
            case False, True:
                return lambda v: v <= maximum
        msg = "Invalid range filter configuration: minimum must be non-negative and maximum must be finite."
        raise ValueError(msg)
