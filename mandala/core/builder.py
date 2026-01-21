"""Builder module for Mandala core functionality."""

from __future__ import annotations

from random import Random
from typing import TYPE_CHECKING

from mandala.config.config import Filecount, Filename, Folder, ListIncludeExclude, MinMax
from mandala.core.timestamp import DateTimeSingleton

from .engine import MandalaEngine
from .quota import DiversityQuota
from .reporter import ReportWriter
from .trash import TrashHandler
from .validator import FileValidator
from .walker import RandomFSWalker

if TYPE_CHECKING:
    from ..config.config import MandalaConfig


def _build_rng() -> Random:
    """Build and return a Random instance with a system-generated seed."""
    sys_rand = Random()
    rng_seed = sys_rand.randint(0, 2**32 - 1)
    return Random(rng_seed)


def build_engine(cfg: MandalaConfig) -> MandalaEngine:
    """Build and return the Mandala engine based on the configuration."""
    rng = _build_rng()

    filecount = Filecount(
        count=cfg.filecount.count,
        is_rand=cfg.filecount.is_rand,
        min_rand=cfg.filecount.min_rand,
        max_rand=cfg.filecount.max_rand,
        rng=rng,
    )

    # Build FileValidator
    keywords = ListIncludeExclude(
        include=cfg.keyword.include,
        exclude=cfg.keyword.exclude,
        text=cfg.keyword.text,
        re_fmt=r"(.*){}(.*)",
    )
    extensions = ListIncludeExclude(
        include=cfg.extension.include,
        exclude=cfg.extension.exclude,
        text=cfg.extension.text,
        re_fmt=r".{}$",
    )
    filesize = MinMax(
        limit=cfg.filesize.limit,
        minimum=cfg.filesize.minimum,
        maximum=cfg.filesize.maximum,
    )
    duration = MinMax(
        limit=cfg.duration.limit,
        minimum=cfg.duration.minimum,
        maximum=cfg.duration.maximum,
    )
    validator = FileValidator(
        keywords=keywords,
        extensions=extensions,
        filesize=filesize,
        duration=duration,
    )

    # Build other components
    quota = DiversityQuota(
        root=cfg.root,
        unique_folders=cfg.folder.unique,
        max_per_folder=cfg.diversity.max_per_folder,
    )

    trash = TrashHandler(
        empty_folders=cfg.transfermode.trash_empty_folder,
        dry_run=cfg.transfermode.dry_run,
    )

    walker = RandomFSWalker(
        root=cfg.root,
        rng=rng,
        quota=quota,
        trash=trash,
    )

    timestamp = DateTimeSingleton()

    filename = Filename(
        template=cfg.filename.template,
        timestamp=timestamp,
    )

    reporter = ReportWriter(
        root=cfg.root,
        exts_str=extensions.as_string,
        keys_str=keywords.as_string,
        timestamp=timestamp,
    )

    folder = Folder(
        create=cfg.folder.create,
        unique=cfg.folder.unique,
        name=cfg.folder.name,
        count=cfg.folder.count,
        dest=cfg.dest,
    )

    return MandalaEngine(
        root=cfg.root,
        dry_run=cfg.transfermode.dry_run,
        transfer_mode=cfg.transfermode.transfer_mode,
        validator=validator,
        reporter=reporter,
        rng=rng,
        quota=quota,
        trash=trash,
        walker=walker,
        timestamp=timestamp,
        filecount=filecount,
        filename=filename,
        folder=folder,
    )
