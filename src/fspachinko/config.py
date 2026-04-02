"""Translate the configuration model into commands."""

import logging
import re
from dataclasses import dataclass, field
from os.path import isabs, realpath
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, field_validator, model_validator

from fspachinko.constants import SIZE_MAP, TIME_MAP, FilenameTemplate, FilterName, ReStrFmt, TransferMode

if TYPE_CHECKING:
    import random
    from collections.abc import Callable, Iterator

    from fspachinko.adapters.filenamer import AbstractFilenamer
    from fspachinko.adapters.filesystem import AbstractFilesystem
    from fspachinko.adapters.fswalker import AbstractFSWalker
    from fspachinko.adapters.pipeline import AbstractPipeline
    from fspachinko.domain.model import DestinationDirectory, FSEntry

logger = logging.getLogger(__name__)


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
    is_create_unique_dirs: bool = False
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

    root: str = "C:/"
    dest: str = "/fspachinko_output"
    filecount: FilecountModel = Field(default_factory=FilecountModel)
    directory: DirectoryModel = Field(default_factory=DirectoryModel)
    filename: FilenameModel = Field(default_factory=FilenameModel)
    dirname: TextFilterModel = Field(default_factory=TextFilterModel)
    keyword: TextFilterModel = Field(default_factory=TextFilterModel)
    extension: TextFilterModel = Field(default_factory=TextFilterModel)
    filesize: RangeFilterModel = Field(default_factory=RangeFilterModel)
    duration: RangeFilterModel = Field(default_factory=RangeFilterModel)
    options: OptionsModel = Field(default_factory=OptionsModel)

    @field_validator("root", "dest")
    @classmethod
    def validate_root_and_dest_paths(cls, val: str) -> str:
        """Ensure root and dest paths are absolute."""
        if not isabs(val):
            return realpath(val)
        return val


def dict_to_config(config: dict) -> ConfigModel:
    """Convert a dictionary to a ConfigModel."""
    try:
        return ConfigModel.model_validate(config)
    except Exception:
        logger.exception("Failed to convert dictionary to ConfigModel. %s", config)
        raise


def json_to_config(path: str) -> ConfigModel:
    """Load a ConfigModel from a JSON file."""
    try:
        with open(path, encoding="utf-8") as f:
            data = f.read()
        return ConfigModel.model_validate_json(data)
    except Exception:
        logger.exception("Failed to load configuration from JSON file: %s", path)
        raise


@dataclass(slots=True)
class ConfigToFileFilter:
    """Bootstrapper for translating configuration into a file filter function."""

    get_duration: Callable
    filter_name: type[FilterName] = FilterName
    re_str_fmt: type[ReStrFmt] = ReStrFmt
    size_map: dict[str, int] = field(default_factory=lambda: SIZE_MAP)
    time_map: dict[str, int] = field(default_factory=lambda: TIME_MAP)

    def __call__(self, c: ConfigModel) -> Callable:
        """Translate the configuration into a file filter function."""
        filters = {}
        text_specs = (
            (c.dirname, self.filter_name.DIRNAME, self.re_str_fmt.DIRECTORY),
            (c.keyword, self.filter_name.KEYWORD, self.re_str_fmt.KEYWORD),
            (c.extension, self.filter_name.EXTENSION, self.re_str_fmt.EXTENSION),
        )
        for model, name, re_fmt in text_specs:
            filters[name] = self.create_text_filter(
                text=model.text,
                re_fmt=re_fmt,
                is_enabled=model.is_enabled,
                should_include=model.should_include,
            )
        range_specs = (
            (c.filesize, self.filter_name.FILESIZE, self.size_map),
            (c.duration, self.filter_name.DURATION, self.time_map),
        )
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
            self.filter_name.DIRNAME: lambda e, fn: fn(e.parent),
            self.filter_name.KEYWORD: lambda e, fn: fn(e.stem),
            self.filter_name.EXTENSION: lambda e, fn: fn(e.ext),
            self.filter_name.FILESIZE: lambda e, fn: fn(e.size),
            self.filter_name.DURATION: lambda e, fn: fn(self.get_duration(e.path)),
        }
        if filter_fn := filter_mapping.get(name):
            return lambda e, fn=fn: filter_fn(e, fn)
        msg = f"Invalid filter name: {name}"
        raise ValueError(msg)

    def create_text_filter(self, text: str, re_fmt: str, *, is_enabled: bool, should_include: bool) -> Any:
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


@dataclass(slots=True)
class ConfigModelBootstrapper:
    """Bootstrapper for translating configuration into commands."""

    pipeline: AbstractPipeline
    filesystem: AbstractFilesystem
    available_transfer_fns: dict[str, Callable]
    template_filenamer: type[AbstractFilenamer]
    walker: type[AbstractFSWalker]
    rng: random.Random
    config_to_file_filter: Callable
    transfer_mode: type[TransferMode] = TransferMode

    def apply(self, c: ConfigModel) -> None:
        """Translate the configuration into commands."""
        self.rng.seed(c.options.rng_seed)
        self.pipeline.filefilter_fn = self.config_to_file_filter(c)
        self.pipeline.get_new_path_fn = self._build_get_new_path_fn(c)
        self.pipeline.transfer_fn = self._build_transfer_fn(c)
        self.pipeline.walker_fn = self._build_walker_fn(c)

    def _build_get_new_path_fn(self, c: ConfigModel) -> Callable[[DestinationDirectory, FSEntry], str | None]:
        """Build the get_new_path function based on the configuration."""
        filenamer = self.template_filenamer(c.filename.template) if c.filename.is_enabled else None
        return lambda dst, e, fn=filenamer: self._get_new_path_fn(dst, e, fn)

    def _get_new_path_fn(self, dst: DestinationDirectory, e: FSEntry, filenamer: Callable | None = None) -> str | None:
        """Check if the original file name can be used without transfer."""
        new_stem = filenamer(e, dst.count) if filenamer else e.stem
        suffix = e.ext.casefold()
        target = self.filesystem.join_path(dst.path, f"{new_stem}{suffix}")
        if target not in dst.files:
            return target
        # If the file already exists and is the same, skip transferring it.
        if self.filesystem.are_files_identical(e.path, target):
            return None
        return self.filesystem.get_unique_path(target, dst.files)

    def _build_transfer_fn(self, c: ConfigModel) -> Callable:
        """Build the transfer function based on the configuration."""
        return self.available_transfer_fns.get(
            c.options.transfer_mode, self.available_transfer_fns[self.transfer_mode.DRY_RUN]
        )

    def _build_walker_fn(self, c: ConfigModel) -> Callable:
        """Build the walker function based on the configuration."""
        return self.walker(
            root=c.root,
            should_follow_symlink=c.options.should_follow_symlink,
            rng_random_fn=self.rng.random,
            rng_choice_fn=self.rng.choice,
        )

    def build_inputs(self, c: ConfigModel) -> Iterator[tuple[str, int, bool]]:
        """Build the inputs for the pipeline based on the configuration."""
        dst = c.dest
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
