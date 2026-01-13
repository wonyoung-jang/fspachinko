"""Pydantic schemas for Mandala configuration."""

from pathlib import Path

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


class FilesizeModel(BaseModel):
    """Model for size filter."""

    limit: bool = False
    minimum: float = 0.0
    maximum: float = 0.0


class DurationModel(BaseModel):
    """Model for duration filter."""

    limit: bool = False
    minimum: float = 0.0
    maximum: float = 0.0


class FilenameModel(BaseModel):
    """Model for file renaming."""

    is_index: bool = False
    is_rename: bool = False
    rename_to: str = ""


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
