"""Translate the configuration model into commands."""

import logging
import re
from collections import deque
from dataclasses import dataclass
from functools import cache
from os.path import isabs, realpath
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, field_validator, model_validator

from fspachinko.adapters.duration import duration_fn_factory, get_duration_null
from fspachinko.constants import SIZE_MAP, TIME_MAP, FilenameTemplate, FilterName, ReStrFmt, TransferMode
from fspachinko.datapaths import configs_path, get_config_path

if TYPE_CHECKING:
    import random
    from collections.abc import Callable, Iterator, Sequence

    from fspachinko.adapters.filenamer import AbstractFilenamer
    from fspachinko.adapters.filesystem import AbstractFilesystem
    from fspachinko.adapters.fswalker import AbstractFSWalker
    from fspachinko.adapters.pipeline import AbstractPipeline
    from fspachinko.domain.model import DestinationDirectory, FSEntry

logger = logging.getLogger(__name__)


class PathSelectorModel(BaseModel):
    """Model for path selection configuration."""

    path: str = Field(default="")

    @field_validator("path")
    @classmethod
    def validate_root_and_dest_paths(cls, val: str) -> str:
        """Ensure root and dest paths are absolute."""
        if not isabs(val):
            return realpath(val)
        return val


class FilecountModel(BaseModel):
    """Model for file count configuration."""

    count: int = Field(default=10, ge=1)
    is_rand_enabled: bool = False
    rand_min: int = Field(default=1, ge=1)
    rand_max: int = Field(default=10, ge=2)

    @model_validator(mode="after")
    def validate_filecount_model(self) -> FilecountModel:
        """Validate that rand_min is less than or equal to rand_max."""
        if self.rand_min > self.rand_max:
            msg = "Random minimum cannot be greater than random maximum."
            raise ValueError(msg)
        return self


class DirectoryModel(BaseModel):
    """Model for directory creation configuration."""

    is_enabled: bool = False
    name: str = "fsp_output"
    count: int = 1

    @field_validator("count")
    @classmethod
    def validate_count(cls, val: int) -> int:
        """Validate that count is at least 1."""
        if val <= 0:
            return 1
        return val

    @model_validator(mode="after")
    def validate_directory_model(self) -> DirectoryModel:
        """Validate."""
        if not self.is_enabled:
            self.count = 1
        return self


class FilenameModel(BaseModel):
    """Model for file renaming."""

    is_enabled: bool = False
    template: str = FilenameTemplate.ORIGINAL

    @field_validator("template")
    @classmethod
    def validate_template(cls, val: str) -> str:
        """Validate that the template is not empty."""
        if val.strip() == "":
            return FilenameTemplate.ORIGINAL
        return val


class TextFilterModel(BaseModel):
    """Model for list search filtering."""

    is_enabled: bool = False
    should_include: bool = True
    text: str = ""


class RangeFilterModel(BaseModel):
    """Model for range filter."""

    is_enabled: bool = False
    minimum: float = 0.0
    maximum: float = 10.0
    unit: str = ""

    @model_validator(mode="after")
    def validate_range_filter_model(self) -> RangeFilterModel:
        """Validate that maximum is non-negative."""
        if self.minimum > self.maximum:
            msg = "Minimum cannot be greater than maximum."
            raise ValueError(msg)
        return self

    @field_validator("minimum")
    @classmethod
    def validate_minimum(cls, val: float) -> float:
        """Validate that minimum is non-negative."""
        if val < 0:
            return 0
        return val

    @field_validator("maximum")
    @classmethod
    def validate_maximum(cls, val: float) -> float:
        """Validate that maximum is non-negative."""
        if val <= 0:
            return float("inf")
        return val


class OptionsModel(BaseModel):
    """Model for additional options."""

    transfer_mode: str = TransferMode.DRY_RUN
    max_per_dir: int | float = 0
    should_follow_symlink: bool = False
    rng_seed: int | str | bytes | None = None

    @field_validator("max_per_dir")
    @classmethod
    def validate_max_per_dir(cls, val: float) -> int | float:
        """Validate that max_per_dir is non-negative."""
        if val <= 0:
            return float("inf")
        return val

    @field_validator("rng_seed")
    @classmethod
    def validate_rng_seed(cls, val: int | str | bytes | None) -> int | str | bytes | None:
        """Validate rng_seed."""
        if isinstance(val, str) and val == "":
            return None
        return val


class ConfigModel(BaseModel):
    """Model for configuration."""

    root: PathSelectorModel = Field(default_factory=PathSelectorModel)
    dest: PathSelectorModel = Field(default_factory=PathSelectorModel)
    filecount: FilecountModel = Field(default_factory=FilecountModel)
    directory: DirectoryModel = Field(default_factory=DirectoryModel)
    filename: FilenameModel = Field(default_factory=FilenameModel)
    dirname: TextFilterModel = Field(default_factory=TextFilterModel)
    keyword: TextFilterModel = Field(default_factory=TextFilterModel)
    extension: TextFilterModel = Field(default_factory=TextFilterModel)
    filesize: RangeFilterModel = Field(default_factory=RangeFilterModel)
    duration: RangeFilterModel = Field(default_factory=RangeFilterModel)
    options: OptionsModel = Field(default_factory=OptionsModel)

    @property
    def text_filter_specs(self) -> Sequence[tuple[TextFilterModel, str, str]]:
        """Get text filter specifications."""
        return (
            (self.dirname, FilterName.DIRNAME, ReStrFmt.DIRECTORY),
            (self.keyword, FilterName.KEYWORD, ReStrFmt.KEYWORD),
            (self.extension, FilterName.EXTENSION, ReStrFmt.EXTENSION),
        )

    @property
    def range_filter_specs(self) -> Sequence[tuple[RangeFilterModel, str, dict[str, int]]]:
        """Get range filter specifications."""
        return (
            (self.filesize, FilterName.FILESIZE, SIZE_MAP),
            (self.duration, FilterName.DURATION, TIME_MAP),
        )


def config_to_text_filter(c: ConfigModel) -> Iterator[tuple[str, Callable]]:
    """Translate the configuration into a text filter function."""
    for m, name, re_fmt in c.text_filter_specs:
        if fn := build_text_filter(m.text, re_fmt, is_enabled=m.is_enabled, should_include=m.should_include):
            yield name, fn


@cache
def build_text_filter(text: str, re_fmt: str, *, is_enabled: bool, should_include: bool) -> Callable | None:
    """Create a text filter function."""
    if not (is_enabled and text):
        return None
    patterns = tuple(re.compile(re_fmt.format(re.escape(t)), re.IGNORECASE) for t in set(text.split(",")))
    match len(patterns), should_include:
        case 1, True:
            return lambda p: patterns[0].search(p) is not None
        case 1, False:
            return lambda p: patterns[0].search(p) is None
        case _, True:
            return lambda p: any(ptn.search(p) for ptn in patterns)
        case _, False:
            return lambda p: not any(ptn.search(p) for ptn in patterns)


def config_to_range_filter(c: ConfigModel) -> Iterator[tuple[str, Callable]]:
    """Translate the configuration into a range filter function."""
    for m, name, unit_map in c.range_filter_specs:
        mul = unit_map.get(m.unit, 1.0)
        if fn := build_range_filter(m.minimum * mul, m.maximum * mul, is_enabled=m.is_enabled):
            yield name, fn


@cache
def build_range_filter(minimum: float, maximum: float, *, is_enabled: bool) -> Callable | None:
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
        case False, False:
            return None


FILTER_MAP: dict[str, Callable[[FSEntry, Callable], bool]] = {
    FilterName.DIRNAME: lambda e, fn: fn(e.parent),
    FilterName.KEYWORD: lambda e, fn: fn(e.stem),
    FilterName.EXTENSION: lambda e, fn: fn(e.ext),
    FilterName.FILESIZE: lambda e, fn: fn(e.size),
    FilterName.DURATION: lambda e, fn: fn(e.duration),
}


def get_valid_filters(filters: Sequence[tuple[str, Callable | None]]) -> Iterator[Callable]:
    """Get valid filter functions from the configuration."""
    for name, fn in filters:
        if fn is not None and name in FILTER_MAP:
            yield lambda e, fn=fn, name=name: FILTER_MAP[name](e, fn)


def config_to_file_filter(c: ConfigModel) -> Callable:
    """Translate the configuration into a file filter function."""
    filter_from_config = (*config_to_text_filter(c), *config_to_range_filter(c))
    filter_fn = tuple(get_valid_filters(filter_from_config))
    match len(filter_fn):
        case 0:
            return lambda _: True
        case 1:
            return filter_fn[0]
        case _:
            return lambda e: all(f(e) for f in filter_fn)


@dataclass(slots=True)
class ConfigModelBootstrapper:
    """Bootstrapper for translating configuration into commands."""

    pipeline: AbstractPipeline
    filesystem: AbstractFilesystem
    available_transfer_fns: dict[str, Callable]
    template_filenamer: type[AbstractFilenamer]
    walker: type[AbstractFSWalker]
    rng: random.Random
    transfer_mode: type[TransferMode] = TransferMode

    def apply(self, c: ConfigModel) -> None:
        """Translate the configuration into commands."""
        self.rng.seed(c.options.rng_seed)
        duration_fn = duration_fn_factory()
        if not c.duration.is_enabled:
            duration_fn = get_duration_null
        self.pipeline.filefilter_fn = config_to_file_filter(c)
        self.pipeline.get_new_path_fn = self._build_get_new_path_fn(c)
        self.pipeline.transfer_fn = self._build_transfer_fn(c.options.transfer_mode)
        self.pipeline.walker_fn = self._build_walker_fn(c)
        self.pipeline.duration_fn = duration_fn
        self.pipeline.inputs = deque(self._build_inputs(c))

    def _build_get_new_path_fn(self, c: ConfigModel) -> Callable[[DestinationDirectory, FSEntry], str | None]:
        """Build the get_new_path function based on the configuration."""
        filename_fn = self.template_filenamer(c.filename.template) if c.filename.is_enabled else None
        return lambda dst, e, fn=filename_fn: self._get_new_path_fn(dst, e, fn)

    def _get_new_path_fn(
        self, dst: DestinationDirectory, e: FSEntry, filename_fn: Callable | None = None
    ) -> str | None:
        """Check if the original file name can be used without transfer."""
        new_stem = filename_fn(e, dst.count) if filename_fn else e.stem
        suffix = e.ext.casefold()
        target = self.filesystem.join_path(dst.path, f"{new_stem}{suffix}")
        if target not in dst.files:
            return target
        # The target name is already in the destination.
        # Check if the existing name is the same file.
        # Cases when it may not be:
        #   2026_04_05/audio.mp4, 2026_04_05/audio.mp4
        #   Same name in two different source directories, but different files
        if self.filesystem.are_files_identical(e.path, target):
            # If the files are the same, then this is not a valid file transfer
            return None
        # If the files are different, find a new name for it so there's no overwriting or errors
        return self.filesystem.get_unique_path(target, dst.files)

    def _build_transfer_fn(self, mode: str) -> Callable:
        """Build the transfer function based on the configuration."""
        if mode in self.available_transfer_fns:
            return self.available_transfer_fns[mode]
        return self.available_transfer_fns[self.transfer_mode.DRY_RUN]

    def _build_walker_fn(self, c: ConfigModel) -> Callable:
        """Build the walker function based on the configuration."""
        return self.walker(
            root=c.root.path,
            should_follow_symlink=c.options.should_follow_symlink,
            rng=self.rng,
        )

    def _build_inputs(self, c: ConfigModel) -> Iterator[tuple[str, int, bool]]:
        """Build the inputs for the pipeline based on the configuration."""
        dst = c.dest.path
        cf = c.filecount
        cd = c.directory
        filecount_fn = (
            (lambda: self.rng.randint(cf.rand_min, cf.rand_max)) if cf.is_rand_enabled else (lambda: cf.count)
        )
        if not cd.is_enabled:
            yield (dst, filecount_fn(), False)
            return
        existing = self.filesystem.get_existing_subdirs(dst)
        candidate = self.filesystem.join_path(dst, cd.name)
        for _ in range(cd.count):
            next_name = self.filesystem.get_unique_path(candidate, existing)
            yield (next_name, filecount_fn(), True)
            existing.add(next_name)


@dataclass(slots=True)
class ConfigManager:
    """Manager for configuration files."""

    fs: AbstractFilesystem
    directory: str = configs_path()
    _current: str = ""

    @property
    def current(self) -> str:
        """Get the current configuration file name."""
        return self._current

    @current.setter
    def current(self, p: str) -> None:
        """Set the current configuration file name."""
        self._current = get_config_path(p)

    def get_configs(self) -> list[str]:
        """Get a list of available configuration files."""
        return self.fs.get_existing_json_files(self.directory)
