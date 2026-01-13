"""Pydantic schemas for Mandala configuration."""

from pathlib import Path

from pydantic import BaseModel, Field


class MandalaConfigModel(BaseModel):
    """Dataclass for Mandala configuration."""

    # Paths
    root: Path = Field(default_factory=Path)
    dest: Path = Field(default_factory=Path)
    # File Count
    num_files: int = 0
    is_rand_file_count: bool = False
    num_files_rand_min: int = 0
    num_files_rand_max: int = 0
    # Filter Keywords
    is_keywords_include: bool = False
    is_keywords_exclude: bool = False
    keywords: list[str] = Field(default_factory=list)
    # Filter Extensions
    is_extensions_include: bool = False
    is_extensions_exclude: bool = False
    extensions: list[str] = Field(default_factory=list)
    # Filter Size
    limit_size: bool = False
    min_size: float = 0.0
    max_size: float = 0.0
    # Filter Duration
    limit_duration: bool = False
    min_duration: float = 0.0
    max_duration: float = 0.0
    # Filter Weight
    weight_top: int = 0
    weight_bottom: int = 0
    # Folder Creation
    create_folders: bool = False
    folder_name: str = ""
    unique_folders: bool = True
    num_folders: int = 1
    # Renaming
    index_files: bool = False
    rename_files: bool = False
    rename_name: str = ""
    # Trash
    trash_empty_folders: bool = False
    trash_source_files: bool = False
    trash_invalid_files: bool = False
    # Invalid
    log_invalid: bool = True
    # Stall time
    stall_time_limit: float = 0.0


class DurationFilterModel(BaseModel):
    """Dataclass for duration filter configuration."""

    limit_duration: bool = False
    min_duration: float = 0.0
    max_duration: float = 0.0
