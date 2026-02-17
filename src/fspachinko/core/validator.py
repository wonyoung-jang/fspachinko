"""Config validation functions."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .config import ListIncludeExclude, MinMax
from .constants import SIZE_MAP, TIME_MAP, ReStrFmt
from .helpers import get_duration

if TYPE_CHECKING:
    from collections.abc import Callable

    from .config import ConfigModel
    from .walker import FSEntry


def build_file_validator(m: ConfigModel) -> FileValidator:
    """Build and return a FileValidator based on the configuration."""
    dirname = ListIncludeExclude.from_model(m.directory_name, re_fmt=ReStrFmt.DIRECTORY)
    keywords = ListIncludeExclude.from_model(m.keyword, re_fmt=ReStrFmt.KEYWORD)
    extensions = ListIncludeExclude.from_model(m.extension, re_fmt=ReStrFmt.EXTENSION)
    filesize = MinMax.from_model(m.filesize, mapping=SIZE_MAP)
    duration = MinMax.from_model(m.duration, mapping=TIME_MAP)

    validators = []
    if dirname.is_enabled:
        validators.append(DirnameFilter(dirname))
    if keywords.is_enabled:
        validators.append(KeywordFilter(keywords))
    if extensions.is_enabled:
        validators.append(ExtensionFilter(extensions))
    if filesize.is_enabled:
        validators.append(FilesizeFilter(filesize))
    if duration.is_enabled:
        validators.append(DurationFilter(duration))

    return FileValidator(validators=tuple(validators))


@dataclass(slots=True)
class DirnameFilter:
    """Validator for parent directory names."""

    dirname: ListIncludeExclude

    def __call__(self, entry: FSEntry) -> bool:
        """Validate the parent directory name."""
        return self.dirname.is_valid(entry.parent)


@dataclass(slots=True)
class KeywordFilter:
    """Validator for filename keywords."""

    keywords: ListIncludeExclude

    def __call__(self, entry: FSEntry) -> bool:
        """Validate the filename stem against keywords."""
        return self.keywords.is_valid(entry.stem)


@dataclass(slots=True)
class ExtensionFilter:
    """Validator for file extensions."""

    extensions: ListIncludeExclude

    def __call__(self, entry: FSEntry) -> bool:
        """Validate the file extension."""
        return self.extensions.is_valid(entry.ext)


@dataclass(slots=True)
class FilesizeFilter:
    """Validator for file size."""

    filesize: MinMax

    def __call__(self, entry: FSEntry) -> bool:
        """Validate the file size."""
        return self.filesize.is_valid(entry.size)


@dataclass(slots=True)
class DurationFilter:
    """Validator for file duration."""

    duration: MinMax

    def __call__(self, entry: FSEntry) -> bool:
        """Validate the file duration."""
        return self.duration.is_valid(get_duration(entry.path))


@dataclass(slots=True)
class FileValidator:
    """Class for validating files based on configuration."""

    validators: tuple[Callable[[FSEntry], bool], ...]

    def __call__(self, entry: FSEntry) -> bool:
        """Check if a file is valid based on the current filters."""
        return all(validator(entry) for validator in self.validators)
