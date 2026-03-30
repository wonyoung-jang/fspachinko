"""Translate the configuration model into commands."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from fspachinko.constants import SIZE_MAP, TIME_MAP, FilterName, ReStrFmt

if TYPE_CHECKING:
    from collections.abc import Callable

    from fspachinko.adapters.filenamer import AbstractFilenamer
    from fspachinko.adapters.filesystem import AbstractFilesystem
    from fspachinko.adapters.fswalker import AbstractFSWalker
    from fspachinko.adapters.pipeline import AbstractPipeline
    from fspachinko.adapters.transfer import AbstractTransferFnManager
    from fspachinko.configuration.model import ConfigModel
    from fspachinko.domain.model import DestinationDirectory, FSEntry


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


@dataclass(slots=True)
class ConfigToPipeline:
    """Bootstrapper for translating configuration into commands."""

    pipeline: AbstractPipeline
    filesystem: AbstractFilesystem
    rng_seed_fn: Callable
    transfer_fn_manager: AbstractTransferFnManager
    template_filenamer: type[AbstractFilenamer]
    walker: type[AbstractFSWalker]
    randcount_fn: Callable
    get_text_patterns: Callable
    config_to_file_filter: Callable

    def apply(self, c: ConfigModel) -> None:
        """Translate the configuration into commands."""
        self.rng_seed_fn(c.options.rng_seed)
        self.pipeline.is_create_dir = c.directory.is_enabled
        self.pipeline.transfer_fn = self.transfer_fn_manager.get_transfer_fn(c.options.transfer_mode)
        self.pipeline.walker_fn = self.walker(root=c.root, should_follow_symlink=c.options.should_follow_symlink)
        filecount_fn = (
            (lambda rnge=(c.filecount.rand_min, c.filecount.rand_max): self.randcount_fn(*rnge))
            if c.filecount.is_rand_enabled
            else (lambda count=c.filecount.count: count)
        )
        if not c.directory.is_enabled:
            self.pipeline.dest_dir_inputs.append((c.dest, filecount_fn()))
            return
        existing = self.filesystem.get_existing_subdirs(c.dest)
        candidate = self.filesystem.join_path(c.dest, c.directory.name)
        while len(self.pipeline.dest_dir_inputs) < c.directory.count:
            next_name = self.filesystem.get_unique_path(candidate, existing)
            self.filesystem.make_directory(next_name)
            self.pipeline.dest_dir_inputs.append((next_name, filecount_fn()))
            existing.add(next_name)
        self.pipeline.filefilter_fn = self.config_to_file_filter(c)
        filenamer = self.template_filenamer(c.filename.template) if c.filename.is_enabled else None
        self.pipeline.get_new_path_fn = lambda dst, e, fn=filenamer: self._get_new_path_fn(dst, e, fn)

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
