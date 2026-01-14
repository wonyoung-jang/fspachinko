"""Mandala configuration dataclass."""

from dataclasses import dataclass
from pathlib import Path

from ..config.schemas import (
    DiversityModel,
    DualListFilterModel,
    DurationModel,
    ExecutionModel,
    FilecountModel,
    FilenameModel,
    FilesizeModel,
    FoldersModel,
    TrashModel,
)


@dataclass(slots=True)
class MandalaConfig:
    """Dataclass for Mandala configuration."""

    root: Path
    dest: Path

    count_model: FilecountModel

    folders_model: FoldersModel
    filename_model: FilenameModel
    trash_model: TrashModel

    keywords_model: DualListFilterModel
    extensions_model: DualListFilterModel

    size_model: FilesizeModel
    duration_model: DurationModel
    diversity_model: DiversityModel

    execution_model: ExecutionModel
