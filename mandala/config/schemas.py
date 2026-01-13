"""Pydantic schemas for Mandala configuration."""

import filecmp
from pathlib import Path
from random import Random

from pydantic import BaseModel, Field


class KeywordsModel(BaseModel):
    """Model for keyword filtering."""

    include: bool = False
    exclude: bool = False
    text: list[str] = Field(default_factory=list)


class ExtensionsModel(BaseModel):
    """Model for extension filtering."""

    include: bool = False
    exclude: bool = False
    text: list[str] = Field(default_factory=list)


class LimitMinMaxModel(BaseModel):
    """Base model for limit, minimum, and maximum fields."""

    limit: bool = False
    minimum: float = 0.0
    maximum: float = 0.0

    def check(self, value: float) -> bool:
        """Check if a value is within the specified range."""
        if not self.limit:
            return True
        return self.minimum <= value <= self.maximum


class FilesizeModel(LimitMinMaxModel):
    """Model for size filter."""


class DurationModel(LimitMinMaxModel):
    """Model for duration filter."""


class FilenameModel(BaseModel):
    """Model for file renaming."""

    is_index: bool = False
    is_rename: bool = False
    rename_to: str = ""

    def calc_dest_file_path(self, chosen: Path, dest: Path, index: int) -> Path | None:
        """Calculate the destination file path based on naming conventions."""
        ext = chosen.suffix
        stem = chosen.stem

        if self.is_index:
            name = f"{index + 1}_{stem}{ext}"
        elif self.is_rename:
            name = f"{self.rename_to}_{index + 1}{ext}"
        else:
            name = chosen.name

        target = dest / name

        if target.exists() and filecmp.cmp(chosen, target) and not (self.is_rename or self.is_index):
            return None

        x = 2
        base_stem = target.stem
        while target.exists():
            target = dest / f"{base_stem} ({x}){ext}"
            x += 1

        return target


class FoldersModel(BaseModel):
    """Model for folder creation configuration."""

    create: bool = False
    unique: bool = True
    name: str = ""
    count: int = 1


class FilecountModel(BaseModel):
    """Model for file count configuration."""

    count: int = 0
    is_rand_count: bool = False
    count_min_rand: int = 0
    count_max_rand: int = 0

    def get_target(self, rng: Random) -> int:
        """Get the number of files to process for the current folder."""
        if self.is_rand_count:
            return rng.randint(self.count_min_rand, self.count_max_rand)
        return self.count


class TrashModel(BaseModel):
    """Model for trash configuration."""

    empty_folder: bool = False
    source_file: bool = False
    invalid_file: bool = False


class DiversityModel(BaseModel):
    """Model for diversity quota configuration."""

    root_limit: int = 0
    leaf_limit: int = 0


class ExecutionModel(BaseModel):
    """Model for execution configuration."""

    log_invalid: bool = True
    stall_time_limit: float = 0.0


class MandalaConfigModel(BaseModel):
    """Model for Mandala configuration."""

    root: Path
    dest: Path

    count_model: FilecountModel

    folders_model: FoldersModel
    filename_model: FilenameModel
    trash_model: TrashModel

    keywords_model: KeywordsModel
    extensions_model: ExtensionsModel

    size_model: FilesizeModel
    duration_model: DurationModel
    diversity_model: DiversityModel

    execution_model: ExecutionModel
