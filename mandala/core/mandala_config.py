"""Mandala configuration dataclass."""

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class MandalaConfig:
    """Dataclass for Mandala configuration."""

    root: Path = field(default_factory=Path)
    root_absolute: Path = field(default_factory=Path)
    dest: Path = field(default_factory=Path)

    num_files: int = 0

    # Filter Keywords and Extensions
    keywords: list[str] = field(default_factory=list)
    not_keywords: list[str] = field(default_factory=list)
    extensions: list[str] = field(default_factory=list)
    not_extensions: list[str] = field(default_factory=list)

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

    def is_extension(self, source: Path) -> bool:
        """Check if a file has the specified extensions."""
        if not self.extensions:
            return True

        for extension in self.extensions:
            if re.compile(rf"\.{extension}$", re.IGNORECASE).search(source.suffix) is not None:
                return True

        return False

    def is_keyword(self, source: Path) -> bool:
        """Check if a file contains the specified keywords."""
        if not self.keywords:
            return True

        for keyword in self.keywords:
            if re.compile(rf"(.*){keyword}(.*)", re.IGNORECASE).search(source.stem) is not None:
                return True

        return False
