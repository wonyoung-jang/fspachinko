"""Mandala configuration dataclass."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .schemas import (
    DiversityModel,
    ExecutionModel,
    FilecountModel,
    FilenameModel,
    FolderModel,
    LimitMinMaxModel,
    ListIncludeExcludeModel,
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
    filecount: FilecountModel
    folder: FolderModel
    filename: FilenameModel
    trash: TrashModel
    keyword: ListIncludeExcludeModel
    extension: ListIncludeExcludeModel
    filesize: LimitMinMaxModel
    duration: LimitMinMaxModel
    diversity: DiversityModel
    execution: ExecutionModel

    @classmethod
    def from_json(cls, path: Path) -> MandalaConfig:
        """Load configuration from a JSON file."""
        model = MandalaConfigModel.model_validate_json(path.read_text())
        return MandalaConfig(**model.__dict__)
