"""Builder module for Mandala core functionality."""

from __future__ import annotations

from random import Random
from typing import TYPE_CHECKING

from .engine import MandalaEngine
from .quota import DiversityQuota
from .reporter import ReportWriter
from .trash import TrashHandler
from .validator import FileValidator
from .walker import RandomFSWalker

if TYPE_CHECKING:
    from ..config.config import MandalaConfig


def build_engine(config: MandalaConfig) -> MandalaEngine:
    """Build and return the Mandala engine based on the configuration."""
    validator = FileValidator(config)
    reporter = ReportWriter(config)
    quota = DiversityQuota(
        root=config.root,
        unique_folders=config.folder.unique,
        limit_root_folder=config.diversity.root_limit,
        limit_leaf_folder=config.diversity.leaf_limit,
    )

    trash = TrashHandler(
        trash_source_files=config.trash.source_file,
        trash_invalid_files=config.trash.invalid_file,
        trash_empty_folders=config.trash.empty_folder,
        dry_run=config.execution.dry_run,
    )

    sys_rand = Random()
    rng_seed = sys_rand.randint(0, 2**32 - 1)
    rng = Random(rng_seed)

    walker = RandomFSWalker(
        root=config.root,
        rng=rng,
        quota=quota,
        trash=trash,
    )

    return MandalaEngine(
        config=config,
        validator=validator,
        reporter=reporter,
        rng=rng,
        quota=quota,
        trash=trash,
        walker=walker,
    )
