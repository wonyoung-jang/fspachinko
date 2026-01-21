"""Builder module for Mandala core functionality."""

from __future__ import annotations

from random import Random
from typing import TYPE_CHECKING

from ..config.config import Filecount, Filename, Folder, ListIncludeExclude, MinMax
from .engine import MandalaEngine
from .quota import DiversityQuota
from .reporter import ReportWriter
from .timestamp import DateTimeSingleton
from .trash import TrashHandler
from .validator import FileValidator
from .walker import RandomFSWalker

if TYPE_CHECKING:
    from ..config.schemas import MandalaConfigModel


def _build_rng() -> Random:
    """Build and return a Random instance with a system-generated seed."""
    sys_rand = Random()
    rng_seed = sys_rand.randint(0, 2**32 - 1)
    return Random(rng_seed)


def build_engine(m: MandalaConfigModel) -> MandalaEngine:
    """Build and return the Mandala engine based on the configuration."""
    rng = _build_rng()

    filecount = Filecount(
        count=m.filecount.count,
        is_rand=m.filecount.is_rand,
        min_rand=m.filecount.min_rand,
        max_rand=m.filecount.max_rand,
        rng=rng,
    )

    # Build FileValidator
    keywords = ListIncludeExclude(
        include=m.keyword.include,
        exclude=m.keyword.exclude,
        text=m.keyword.text,
        re_fmt=r"(.*){}(.*)",
    )
    extensions = ListIncludeExclude(
        include=m.extension.include,
        exclude=m.extension.exclude,
        text=m.extension.text,
        re_fmt=r".{}$",
    )
    filesize = MinMax(
        limit=m.filesize.limit,
        minimum=m.filesize.minimum,
        maximum=m.filesize.maximum,
    )
    duration = MinMax(
        limit=m.duration.limit,
        minimum=m.duration.minimum,
        maximum=m.duration.maximum,
    )
    validator = FileValidator(
        keywords=keywords,
        extensions=extensions,
        filesize=filesize,
        duration=duration,
    )

    # Build other components
    quota = DiversityQuota(
        root=m.root,
        unique_folders=m.folder.unique,
        max_per_folder=m.diversity.max_per_folder,
    )

    trash = TrashHandler(
        empty_folders=m.transfermode.trash_empty_folder,
        dry_run=m.transfermode.dry_run,
    )

    walker = RandomFSWalker(
        root=m.root,
        rng=rng,
        quota=quota,
        trash=trash,
    )

    timestamp = DateTimeSingleton()

    reporter = ReportWriter(
        root=m.root,
        exts_str=extensions.as_string,
        keys_str=keywords.as_string,
        timestamp=timestamp,
    )

    filename = Filename(
        template=m.filename.template,
        timestamp=timestamp,
    )
    folder = Folder(
        create=m.folder.create,
        unique=m.folder.unique,
        name=m.folder.name,
        count=m.folder.count,
        dest=m.dest,
    )

    return MandalaEngine(
        root=m.root,
        dry_run=m.transfermode.dry_run,
        transfer_mode=m.transfermode.transfer_mode,
        validator=validator,
        reporter=reporter,
        quota=quota,
        trash=trash,
        walker=walker,
        timestamp=timestamp,
        filecount=filecount,
        filename=filename,
        folder=folder,
    )
