"""Pydantic schemas for Mandala configuration."""

from pathlib import Path

from pydantic import BaseModel, Field


class FilecountModel(BaseModel):
    """Model for file count configuration."""

    count: int = 0
    is_rand_count: bool = False
    count_min_rand: int = 0
    count_max_rand: int = 0


class FolderModel(BaseModel):
    """Model for folder creation configuration."""

    create: bool = False
    unique: bool = True
    name: str = ""
    count: int = 1


class FilenameModel(BaseModel):
    """Model for file renaming."""

    is_index: bool = False
    is_rename: bool = False
    rename_to: str = ""


class TrashModel(BaseModel):
    """Model for trash configuration."""

    empty_folder: bool = False
    source_file: bool = False
    invalid_file: bool = False


class ListIncludeExcludeModel(BaseModel):
    """Model for list filtering."""

    include: bool = False
    exclude: bool = False
    text: list[str] = Field(default_factory=list)


class LimitMinMaxModel(BaseModel):
    """Model for size filter."""

    limit: bool = False
    minimum: float = 0.0
    maximum: float = 0.0


class DiversityModel(BaseModel):
    """Model for diversity quota configuration."""

    root_limit: int = 0
    leaf_limit: int = 0


class ProgressModel(BaseModel):
    """Model for progress tracking."""

    stall_time_limit: float = 0.0


class ExecutionModel(BaseModel):
    """Model for execution configuration."""

    log_invalid: bool = True
    dry_run: bool = False


class MandalaConfigModel(BaseModel):
    """Model for Mandala configuration."""

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
    progress: ProgressModel
    execution: ExecutionModel
