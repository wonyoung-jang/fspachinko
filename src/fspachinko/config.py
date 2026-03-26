"""Translate the configuration model into commands."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .constants import SIZE_MAP, TIME_MAP, FilterName, ReStrFmt
from .domain.commands import (
    Command,
    CreateDestDirs,
    CreateFilefilterFn,
    CreateFilenameFn,
    CreateRangeFilterFn,
    CreateTextFilterFn,
    CreateTransferFn,
    CreateTransferJob,
    CreateWalkerFn,
    SetPipelineCreateDir,
    SetRngSeed,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from .configuration.model import ConfigModel
    from .domain.commands import Command


@dataclass(slots=True)
class ConfigBootstrapper:
    """Bootstrapper for translating configuration into commands."""

    config: ConfigModel

    def translate(self) -> Iterator[Command]:
        """Translate the configuration into commands."""
        c = self.config
        yield CreateTransferJob(
            root=c.root,
            max_per_dir=c.options.max_per_dir,
            unique_files_only=c.options.is_create_unique_dirs,
        )
        yield SetRngSeed(
            rng_seed=c.options.rng_seed,
        )
        yield SetPipelineCreateDir(
            is_create_dir=c.directory.is_enabled,
        )
        yield CreateTransferFn(
            transfermode=c.options.transfer_mode,
        )
        yield CreateFilenameFn(
            template=c.filename.template,
            is_enabled=c.filename.is_enabled,
        )
        yield CreateDestDirs(
            dir_count=c.directory.count,
            directory_dest=c.dest,
            directory_name=c.directory.name,
            directory_create_is_enabled=c.directory.is_enabled,
            filecount_static=c.filecount.count,
            filecount_randrange=(c.filecount.rand_min, c.filecount.rand_max),
            filecount_rand_is_enabled=c.filecount.is_rand_enabled,
        )
        yield CreateWalkerFn(
            root=c.root,
            should_follow_symlink=c.options.should_follow_symlink,
        )
        text_specs = [
            (c.dirname, FilterName.DIRNAME, ReStrFmt.DIRECTORY),
            (c.keyword, FilterName.KEYWORD, ReStrFmt.KEYWORD),
            (c.extension, FilterName.EXTENSION, ReStrFmt.EXTENSION),
        ]
        for model, name, re_fmt in text_specs:
            yield CreateTextFilterFn(
                name=name,
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
            yield CreateRangeFilterFn(
                name=name,
                minimum=model.minimum * mul,
                maximum=model.maximum * mul,
                is_enabled=model.is_enabled,
            )
        yield CreateFilefilterFn()
