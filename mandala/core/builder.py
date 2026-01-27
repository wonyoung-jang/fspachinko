"""Builder module for Mandala core functionality."""

from random import Random
from typing import TYPE_CHECKING

from ..config import Filecount, Filename, Folder, ListIncludeExclude, MinMax, SizeLimit
from .engine import MandalaEngine
from .quota import DiversityQuota
from .reporter import ReportWriter
from .state import MandalaEngineContext
from .transfer import fetch_transfer_strategy
from .validator import FileValidator
from .walker import RandomFSWalker

if TYPE_CHECKING:
    from ..config import MandalaConfigModel


def build_engine(m: MandalaConfigModel) -> MandalaEngine:
    """Build and return the Mandala engine based on the configuration."""
    rng = Random()

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
        max_per_folder=m.options.max_per_folder,
    )

    walker = RandomFSWalker(
        root=m.root,
        rng=rng,
        quota=quota,
        follow_symlinks=m.options.follow_symlinks,
    )

    reporter = ReportWriter(
        root=m.root,
        exts_str=extensions.as_string,
        keys_str=keywords.as_string,
    )

    filename = Filename(
        template=m.filename.template,
    )
    folder = Folder(
        create_enabled=m.folder.create_enabled,
        name=m.folder.name,
        count=m.folder.count,
        dest=m.dest,
    )

    folder_size_limit = SizeLimit(
        enabled=m.folder_size_limit.enabled,
        size_limit=m.folder_size_limit.size_limit,
    )
    total_size_limit = SizeLimit(
        enabled=m.total_size_limit.enabled,
        size_limit=m.total_size_limit.size_limit,
    )

    context = MandalaEngineContext(
        folder=folder,
        quota=quota,
        folder_size_limit=folder_size_limit,
        total_size_limit=total_size_limit,
        reporter=reporter,
        dry_run=m.options.dry_run_enabled,
    )

    return MandalaEngine(
        root=m.root,
        walk=walker.walk,
        is_valid=validator.is_valid,
        get_filecount=filecount.get_count,
        get_filename=filename.calc_dest_target,
        transfer_file=fetch_transfer_strategy(m.transfermode.transfer_mode),
        _ctx=context,
    )
