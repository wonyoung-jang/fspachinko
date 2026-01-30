"""Builder module for File Roulette core functionality."""

from random import Random
from typing import TYPE_CHECKING

from ..config import Filecount, Filename, Folder, ListIncludeExclude, MinMax, SizeLimit
from ..utils import ReStrFmt
from .engine import Engine
from .quota import DiversityQuota
from .reporter import ReportWriter
from .state import MainEngineContext
from .transfer import fetch_transfer_strategy
from .validator import FileValidator
from .walker import RandomFSWalker

if TYPE_CHECKING:
    from ..config import ConfigModel


def build_engine(m: ConfigModel) -> Engine:
    """Build and return the File Roulette engine based on the configuration."""
    # Build FileValidator
    validator = FileValidator(
        keywords=ListIncludeExclude.from_model(m.keyword, re_fmt=ReStrFmt.KEYWORD),
        extensions=ListIncludeExclude.from_model(m.extension, re_fmt=ReStrFmt.EXTENSION),
        filesize=MinMax.from_model(m.filesize),
        duration=MinMax.from_model(m.duration),
    )

    # Build other components
    root = m.root
    options = m.options
    rng = Random()
    quota = DiversityQuota(
        root=root,
        unique_folders=m.folder.is_unique,
        max_per_folder=options.max_per_folder,
    )
    walker = RandomFSWalker(
        root=root,
        rng=rng,
        quota=quota,
        should_follow_symlink=options.should_follow_symlink,
    )

    context = MainEngineContext(
        folder=Folder.from_model(m.folder, dest=m.dest),
        quota=quota,
        folder_size_limit=SizeLimit.from_model(m.folder_size_limit),
        total_size_limit=SizeLimit.from_model(m.total_size_limit),
        reporter=ReportWriter(
            root=root,
            exts_str=validator.extensions.as_string,
            keys_str=validator.keywords.as_string,
        ),
        dry_run=options.is_dry_run,
    )

    return Engine(
        root=root,
        walker=walker,
        validator=validator,
        filecount=Filecount.from_model(m.filecount, rng=rng),
        filename=Filename.from_model(m.filename),
        transfer_file=fetch_transfer_strategy(m.transfermode.transfer_mode),
        _ctx=context,
    )
