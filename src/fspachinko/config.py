"""Translate the configuration model into commands."""

import re
from collections import deque
from dataclasses import dataclass
from functools import partial
from os.path import isabs, realpath
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, field_validator, model_validator

from fspachinko.adapters.duration import duration_fn_factory, get_duration_null
from fspachinko.datapaths import configs_path, get_config_path
from fspachinko.domain.model import DestinationDirectory
from fspachinko.fp import Fp

if TYPE_CHECKING:
    import random
    from collections.abc import Callable, Iterator, Sequence

    from fspachinko.adapters.filenamer import AbstractFilenamer
    from fspachinko.adapters.filesystem import AbstractFilesystem
    from fspachinko.adapters.fswalker import AbstractFSWalker
    from fspachinko.adapters.pipeline import AbstractPipeline
    from fspachinko.domain.model import FSEntry


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
    template: str = Fp.FilenameTemplate.ORIGINAL

    @field_validator("template")
    @classmethod
    def validate_template(cls, val: str) -> str:
        """Validate that the template is not empty."""
        if val.strip() == "":
            return Fp.FilenameTemplate.ORIGINAL
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
            return Fp.MAXFLOAT
        return val


class OptionsModel(BaseModel):
    """Model for additional options."""

    transfer_mode: str = Fp.TransferMode.DRY_RUN
    max_per_dir: int | float = 0
    should_follow_symlink: bool = False
    rng_seed: int | str | bytes | None = None

    @field_validator("max_per_dir")
    @classmethod
    def validate_max_per_dir(cls, val: float) -> int | float:
        """Validate that max_per_dir is non-negative."""
        if val <= 0:
            return Fp.MAXFLOAT
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
    def text_filter_specs(self) -> Sequence[tuple[TextFilterModel, Fp.FilterName, Fp.ReStrFmt]]:
        """Get text filter specifications."""
        return (
            (self.dirname, Fp.FilterName.DIRNAME, Fp.ReStrFmt.DIRECTORY),
            (self.keyword, Fp.FilterName.KEYWORD, Fp.ReStrFmt.KEYWORD),
            (self.extension, Fp.FilterName.EXTENSION, Fp.ReStrFmt.EXTENSION),
        )

    @property
    def range_filter_specs(self) -> Sequence[tuple[RangeFilterModel, Fp.FilterName, dict[str, int]]]:
        """Get range filter specifications."""
        return (
            (self.filesize, Fp.FilterName.FILESIZE, Fp.SIZE_MAP),
            (self.duration, Fp.FilterName.DURATION, Fp.TIME_MAP),
        )


def config_to_text_filter(c: ConfigModel) -> Iterator[tuple[Fp.FilterName, Callable]]:
    """Translate the configuration into a text filter function."""
    for m, name, re_fmt in c.text_filter_specs:
        if not m.is_enabled or not m.text:
            continue
        patterns = tuple(re.compile(re_fmt.format(re.escape(t)), re.IGNORECASE) for t in set(m.text.split(",")))
        yield name, build_text_filter(patterns, include=m.should_include)


def build_text_filter(patterns: tuple[re.Pattern, ...], *, include: bool) -> Callable:
    """Create a text filter function."""
    if len(patterns) == 1:
        if include:
            return lambda t: patterns[0].search(t) is not None
        return lambda t: patterns[0].search(t) is None
    if include:
        return lambda t: any(ptn.search(t) for ptn in patterns)
    return lambda t: not any(ptn.search(t) for ptn in patterns)


def config_to_range_filter(c: ConfigModel) -> Iterator[tuple[Fp.FilterName, Callable]]:
    """Translate the configuration into a range filter function."""
    for m, name, unit_map in c.range_filter_specs:
        if not m.is_enabled:
            continue
        mul = unit_map.get(m.unit, 1.0)
        minimum = m.minimum * mul
        maximum = m.maximum * mul
        yield name, lambda v, minimum=minimum, maximum=maximum: minimum <= v <= maximum


FILTER_MAP: dict[Fp.FilterName, Callable[[FSEntry, Callable], bool]] = {
    Fp.FilterName.DIRNAME: lambda e, fn: fn(e.parent),
    Fp.FilterName.KEYWORD: lambda e, fn: fn(e.stem),
    Fp.FilterName.EXTENSION: lambda e, fn: fn(e.ext),
    Fp.FilterName.FILESIZE: lambda e, fn: fn(e.size),
    Fp.FilterName.DURATION: lambda e, fn: fn(e.duration),
}


def get_valid_filters(*filters: tuple[Fp.FilterName, Callable]) -> Sequence[Callable]:
    """Get valid filter functions from the configuration."""
    return tuple(partial(FILTER_MAP[name], fn=fn) for name, fn in filters if name in FILTER_MAP)


def config_to_file_filter(c: ConfigModel) -> Callable:
    """Translate the configuration into a file filter function."""
    file_filters = get_valid_filters(*config_to_text_filter(c), *config_to_range_filter(c))
    nfilters = len(file_filters)
    if nfilters == 0:
        return lambda _: True
    if nfilters == 1:
        return file_filters[0]
    return lambda e, file_filters=file_filters: all(f(e) for f in file_filters)


@dataclass(slots=True)
class ConfigModelBootstrapper:
    """Bootstrapper for translating configuration into commands."""

    fs: AbstractFilesystem
    available_transfer_fns: dict[Fp.TransferMode, Callable]
    template_filenamer: type[AbstractFilenamer]
    walker: type[AbstractFSWalker]
    rng: random.Random

    def apply(self, c: ConfigModel, pipeline: AbstractPipeline) -> None:
        """Translate the configuration into commands."""
        self.rng.seed(c.options.rng_seed)
        pipeline.filefilter_fn = config_to_file_filter(c)
        pipeline.get_new_path_fn = self._build_get_new_path_fn(c)
        pipeline.transfer_fn = self._build_transfer_fn(c)
        pipeline.walker_fn = self._build_walker_fn(c)
        pipeline.duration_fn = duration_fn_factory() if c.duration.is_enabled else get_duration_null
        pipeline.inputs = self._build_inputs(c)

    def _build_get_new_path_fn(self, c: ConfigModel) -> Callable[[DestinationDirectory, FSEntry], str | None]:
        """Build the get_new_path function based on the configuration."""
        filename_fn = self.template_filenamer(template=c.filename.template) if c.filename.is_enabled else None
        return lambda dst, e, fn=filename_fn: self._get_new_path_fn(dst, e, fn)

    def _get_new_path_fn(
        self, dst: DestinationDirectory, e: FSEntry, filename_fn: Callable | None = None
    ) -> str | None:
        """Check if the original file name can be used without transfer."""
        newstem = filename_fn(e, len(dst)) if filename_fn else e.stem
        target = self.fs.join_path(dst.path, f"{newstem}{e.ext}")
        if target not in dst:
            return target
        # The target name is already in the destination.
        # Check if the existing name is the same file.
        # Cases when it may not be:
        #   2026_04_05/audio.mp4, 2026_04_05/audio.mp4
        #   Same name in two different source directories, but different files
        if self.fs.are_files_identical(e.path, target):
            # If the files are the same, then this is not a valid file transfer
            return None
        # If the files are different, find a new name for it so there's no overwriting or errors
        return self.fs.get_unique_path(target, dst)

    def _build_transfer_fn(self, c: ConfigModel) -> Callable[[str, str], None]:
        """Build the transfer function based on the configuration."""
        mode = Fp.TransferMode(c.options.transfer_mode)
        if mode in self.available_transfer_fns:
            return self.available_transfer_fns[mode]
        return self.available_transfer_fns[Fp.TransferMode.DRY_RUN]

    def _build_walker_fn(self, c: ConfigModel) -> Callable[[], Iterator[FSEntry]]:
        """Build the walker function based on the configuration."""
        return self.walker(
            root=c.root.path,
            should_follow_symlink=c.options.should_follow_symlink,
            rng=self.rng,
        )

    def _build_inputs(self, c: ConfigModel) -> deque[DestinationDirectory]:
        """Build the inputs for the pipeline based on the configuration."""
        filecount_fn = self._build_filecount_fn(c.filecount)
        if c.directory.is_enabled:
            return deque(self._build_multi_dst_run(c, filecount_fn))
        return deque([self._build_single_dst_run(c, filecount_fn)])

    def _build_filecount_fn(self, fc: FilecountModel) -> Callable[[], int]:
        """Build the file count function based on the configuration."""
        if fc.is_rand_enabled:
            return lambda: self.rng.randint(fc.rand_min, fc.rand_max)
        return lambda: fc.count

    def _build_single_dst_run(self, c: ConfigModel, filecount_fn: Callable[[], int]) -> DestinationDirectory:
        """Build a single destination run based on the configuration."""
        return DestinationDirectory(path=c.dest.path, target_qty=filecount_fn(), should_create=False)

    def _build_multi_dst_run(self, c: ConfigModel, filecount_fn: Callable[[], int]) -> Iterator[DestinationDirectory]:
        """Build a multi-destination run based on the configuration."""
        existing = self.fs.get_existing_subdirs(c.dest.path)
        candidate = self.fs.join_path(c.dest.path, c.directory.name)
        for _ in range(c.directory.count):
            dstpath = self.fs.get_unique_path(candidate, existing)
            existing.add(dstpath)
            yield DestinationDirectory(path=dstpath, target_qty=filecount_fn(), should_create=True)


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
