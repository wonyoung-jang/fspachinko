"""Translate the configuration model into commands."""

import re
from collections import deque
from dataclasses import dataclass
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


def _get_text_filter(patterns: tuple[re.Pattern, ...], *, include: bool) -> Callable[[str], bool]:
    """Create a text filter function."""
    if len(patterns) == 1:
        if include:
            return lambda t: patterns[0].search(t) is not None
        return lambda t: patterns[0].search(t) is None
    if include:
        return lambda t: any(ptn.search(t) for ptn in patterns)
    return lambda t: not any(ptn.search(t) for ptn in patterns)


def _get_range_filter(minimum: float, maximum: float) -> Callable[[float], bool]:
    """Create a range filter function."""
    return lambda v, _min=minimum, _max=maximum: _min <= v <= _max


@dataclass(slots=True)
class ConfigAdapter:
    """Adapter for translating configuration into commands."""

    _c: ConfigModel

    def config_to_file_filter(self) -> Callable[[FSEntry], bool]:
        """Translate the configuration into a file filter function."""
        filters = (*self._cfg_to_text_filters(), *self._cfg_to_range_filters())
        n = len(filters)
        if n == 0:
            return lambda _: True
        if n == 1:
            return filters[0]
        return lambda e, _filters=filters: all(f(e) for f in _filters)

    def _cfg_to_text_filters(self) -> Iterator[Callable[[FSEntry], bool]]:
        """Translate the configuration into a text filter function."""
        _specs: Sequence[tuple[object, Fp.ReStrFmt, Callable[[FSEntry], str]]] = (
            (self._c.dirname, Fp.ReStrFmt.DIRECTORY, lambda e: e.parent),
            (self._c.keyword, Fp.ReStrFmt.KEYWORD, lambda e: e.stem),
            (self._c.extension, Fp.ReStrFmt.EXTENSION, lambda e: e.ext),
        )
        for model, rgxfmt, func in _specs:
            if not model.is_enabled or not model.text:
                continue
            patterns = tuple(re.compile(rgxfmt.format(re.escape(t)), re.IGNORECASE) for t in set(model.text.split(",")))
            fn = _get_text_filter(patterns, include=model.should_include)
            yield lambda e, fn=fn, func=func: fn(func(e))

    def _cfg_to_range_filters(self) -> Iterator[Callable[[FSEntry], bool]]:
        """Translate the configuration into a range filter function."""
        _specs: Sequence[tuple[object, dict[str, int], Callable[[FSEntry], float]]] = (
            (self._c.filesize, Fp.SIZE_MAP, lambda e: e.size),
            (self._c.duration, Fp.TIME_MAP, lambda e: e.duration),
        )
        for model, unitmap, func in _specs:
            if not model.is_enabled:
                continue
            mul = unitmap.get(model.unit, 1.0)
            calcmin = model.minimum * mul
            calcmax = model.maximum * mul
            fn = _get_range_filter(calcmin, calcmax)
            yield lambda e, fn=fn, func=func: fn(func(e))


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
        _config_adapter = ConfigAdapter(c)
        pipeline.filefilter_fn = _config_adapter.config_to_file_filter()
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
