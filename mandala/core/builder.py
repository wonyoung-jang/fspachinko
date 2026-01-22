"""Builder module for Mandala core functionality."""

from __future__ import annotations

from random import Random
from typing import TYPE_CHECKING

from mandala.core.transfer import fetch_transfer_strategy

from ..config.config import Filecount, Filename, Folder, ListIncludeExclude, MinMax
from .engine import MandalaEngine
from .quota import DiversityQuota
from .reporter import ReportWriter
from .timestamp import DateTimeProvider
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
        is_rand=m.filecount.rand_enabled,
        min_rand=m.filecount.rand_min,
        max_rand=m.filecount.rand_max,
        rng=rng,
    )

    # Build FileValidator
    keywords = ListIncludeExclude(
        include=m.keyword.include_enabled,
        exclude=m.keyword.exclude_enabled,
        text=m.keyword.text,
        re_fmt=r"(.*){}(.*)",
    )
    extensions = ListIncludeExclude(
        include=m.extension.include_enabled,
        exclude=m.extension.exclude_enabled,
        text=m.extension.text,
        re_fmt=r".{}$",
    )
    filesize = MinMax(
        limit=m.filesize.enabled,
        minimum=m.filesize.minimum,
        maximum=m.filesize.maximum,
    )
    duration = MinMax(
        limit=m.duration.enabled,
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
        unique_folders=m.folder.unique_enabled,
        max_per_folder=m.diversity.max_per_folder,
    )

    trash = TrashHandler(
        empty_folders=m.transfermode.trash_empty_folder_enabled,
        dry_run=m.transfermode.dry_run_enabled,
    )

    walker = RandomFSWalker(
        root=m.root,
        rng=rng,
        quota=quota,
        trash=trash,
    )

    timestamp = DateTimeProvider()

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
        create=m.folder.create_enabled,
        unique=m.folder.unique_enabled,
        name=m.folder.name,
        count=m.folder.count,
        dest=m.dest,
    )

    transfer_strategy = fetch_transfer_strategy(m.transfermode.transfer_mode)

    return MandalaEngine(
        root=m.root,
        dry_run=m.transfermode.dry_run_enabled,
        validator=validator,
        reporter=reporter,
        quota=quota,
        trash=trash,
        walker=walker,
        timestamp=timestamp,
        filecount=filecount,
        filename=filename,
        folder=folder,
        transfer=transfer_strategy,
    )
