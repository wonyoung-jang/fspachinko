"""Mandala configuration dataclass."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class MandalaConfig:
    """Dataclass for Mandala configuration."""

    # Paths
    root: Path
    dest: Path

    # File Count
    num_files: int
    is_rand_file_count: bool
    num_files_rand_min: int
    num_files_rand_max: int

    # Filter Keywords and Extensions
    is_keywords: bool
    is_keywords_include: bool
    is_keywords_exclude: bool
    keywords: list[str]

    is_extensions: bool
    is_extensions_include: bool
    is_extensions_exclude: bool
    extensions: list[str]

    # Filter Size
    limit_size: bool
    min_size: float
    max_size: float

    # Filter Duration
    limit_duration: bool
    min_duration: float
    max_duration: float

    # Filter Weight
    weight_top: int
    weight_bottom: int

    # Folder Creation
    create_folders: bool
    folder_name: str
    unique_folders: bool
    num_folders: int

    # Renaming
    index_files: bool
    rename_files: bool
    rename_name: str

    # Trash
    trash_empty_folders: bool
    trash_source_files: bool
    trash_invalid_files: bool

    # Invalid
    log_invalid: bool

    # Stall time
    stall_time_limit: float
