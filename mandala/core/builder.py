"""Builder module for Mandala core functionality."""

from random import Random
from typing import TYPE_CHECKING

from ..config.config import Filecount, Filename, Folder, ListIncludeExclude, MinMax
from ..utils.constants import RNG_RANGE
from .engine import MandalaEngine
from .quota import DiversityQuota
from .reporter import ReportWriter
from .timestamp import DateTimeProvider
from .transfer import fetch_transfer_strategy
from .validator import FileValidator
from .walker import RandomFSWalker

if TYPE_CHECKING:
    from ..config.schemas import MandalaConfigModel


def _build_rng() -> Random:
    """Build and return a Random instance with a system-generated seed."""
    sys_rand = Random()
    rng_seed = sys_rand.randint(*RNG_RANGE)
    return Random(rng_seed)


def build_engine(m: MandalaConfigModel) -> MandalaEngine:
    """Build and return the Mandala engine based on the configuration."""
    rng = _build_rng()

    filecount = Filecount(
        count=m.filecount.count,
        rand_enabled=m.filecount.rand_enabled,
        rand_min=m.filecount.rand_min,
        rand_max=m.filecount.rand_max,
        rng=rng,
    )

    # Build FileValidator
    keywords = ListIncludeExclude(
        include_enabled=m.keyword.include_enabled,
        exclude_enabled=m.keyword.exclude_enabled,
        text=m.keyword.text,
        re_fmt=r"(.*){}(.*)",
    )
    extensions = ListIncludeExclude(
        include_enabled=m.extension.include_enabled,
        exclude_enabled=m.extension.exclude_enabled,
        text=m.extension.text,
        re_fmt=r".{}$",
    )
    filesize = MinMax(
        enabled=m.filesize.enabled,
        minimum=m.filesize.minimum,
        maximum=m.filesize.maximum,
    )
    duration = MinMax(
        enabled=m.duration.enabled,
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

    walker = RandomFSWalker(
        root=m.root,
        rng=rng,
        quota=quota,
        follow_symlinks=m.walker.follow_symlinks,
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
        create_enabled=m.folder.create_enabled,
        name=m.folder.name,
        count=m.folder.count,
        dest=m.dest,
    )

    return MandalaEngine(
        root=m.root,
        dry_run=m.transfermode.dry_run_enabled,
        validator=validator,
        reporter=reporter,
        quota=quota,
        walker=walker,
        timestamp=timestamp,
        filecount=filecount,
        filename=filename,
        folder=folder,
        transfer=fetch_transfer_strategy(m.transfermode.transfer_mode),
    )
