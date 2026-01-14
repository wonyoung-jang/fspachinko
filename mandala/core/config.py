"""Mandala configuration dataclass."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..config.schemas import (
    DiversityModel,
    DualListFilterModel,
    DurationModel,
    ExecutionModel,
    FilecountModel,
    FilenameModel,
    FilesizeModel,
    FoldersModel,
    MandalaConfigModel,
    TrashModel,
)

if TYPE_CHECKING:
    from pathlib import Path


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

    @classmethod
    def from_json(cls, path: Path) -> MandalaConfig:
        """Load configuration from a JSON file."""
        model = MandalaConfigModel.model_validate_json(path.read_text())
        return MandalaConfig(**model.__dict__)
