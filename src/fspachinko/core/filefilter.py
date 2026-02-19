"""Config validation functions."""

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

    filters: tuple[Callable[[FSEntry], bool], ...]

    def __call__(self, entry: FSEntry) -> bool:
        """Check if a file is valid based on the current filters."""
        return all(f(entry) for f in self.filters)


def get_validator(m: ConfigModel) -> FileFilter:
    """Build and return a FileValidator based on the configuration."""
    dirname = get_inc_exc_filter_fn(m.directory_name, re_fmt=ReStrFmt.DIRECTORY)
    keyword = get_inc_exc_filter_fn(m.keyword, re_fmt=ReStrFmt.KEYWORD)
    extension = get_inc_exc_filter_fn(m.extension, re_fmt=ReStrFmt.EXTENSION)
    filesize = get_min_max_filter_fn(m.filesize, mapping=SIZE_MAP)
    duration = get_min_max_filter_fn(m.duration, mapping=TIME_MAP)

    fmap: list[tuple[type, Callable[[Any], bool] | None]] = [
        (DirnameFilter, dirname),
        (KeywordFilter, keyword),
        (ExtensionFilter, extension),
        (FilesizeFilter, filesize),
        (DurationFilter, duration),
    ]
    filters = tuple(c(is_valid=fn) for c, fn in fmap if fn is not None)
    return FileFilter(filters=filters)


@dataclass(slots=True)
class DirnameFilter:
    """Validator for parent directory names."""

    is_valid: Callable[[str], bool]

    def __call__(self, entry: FSEntry) -> bool:
        """Validate the parent directory name."""
        return self.is_valid(entry.parent)


@dataclass(slots=True)
class KeywordFilter:
    """Validator for filename keywords."""

    is_valid: Callable[[str], bool]

    def __call__(self, entry: FSEntry) -> bool:
        """Validate the filename stem against keywords."""
        return self.is_valid(entry.stem)


@dataclass(slots=True)
class ExtensionFilter:
    """Validator for file extensions."""

    is_valid: Callable[[str], bool]

    def __call__(self, entry: FSEntry) -> bool:
        """Validate the file extension."""
        return self.is_valid(entry.ext)


@dataclass(slots=True)
class FilesizeFilter:
    """Validator for file size."""

    is_valid: Callable[[float], bool]

    def __call__(self, entry: FSEntry) -> bool:
        """Validate the file size."""
        return self.is_valid(entry.size)


@dataclass(slots=True)
class DurationFilter:
    """Validator for file duration."""

    is_valid: Callable[[float], bool]

    def __call__(self, entry: FSEntry) -> bool:
        """Validate the file duration."""
        return self.is_valid(get_duration(entry.path))
