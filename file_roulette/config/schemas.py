"""Pydantic schemas for File Roulette configuration."""

import os

from pydantic import BaseModel, field_validator

from ..utils import TransferMode


class FilecountModel(BaseModel):
    """Model for file count configuration."""

    count: int = 0
    is_rand_enabled: bool = False
    rand_min: int = 0
    rand_max: int = 0


class FolderModel(BaseModel):
    """Model for folder creation configuration."""

    should_create: bool = False
    is_unique: bool = True
    name: str = ""
    count: int = 1


class FilenameModel(BaseModel):
    """Model for file renaming."""

    template: str = "{original}"


class TransferModeModel(BaseModel):
    """Model for mode configuration."""

    transfer_mode: str = TransferMode.SYMLINK


class ListIncludeExcludeModel(BaseModel):
    """Model for list filtering."""

    is_enabled: bool = True
    should_include: bool = True
    text: str = ""


class MinMaxModel(BaseModel):
    """Model for size filter."""

    is_enabled: bool = False
    minimum: float = 0.0
    maximum: float = 0.0
    unit: str = ""


class SizeLimitModel(BaseModel):
    """Model for output folder size limits."""

    is_enabled: bool = False
    size_limit: float = 0.0
    unit: str = ""


class OptionsModel(BaseModel):
    """Model for additional options."""

    max_per_folder: int = 0
    should_follow_symlink: bool = False
    is_dry_run: bool = True


class ConfigModel(BaseModel):
    """Model for File Roulette configuration."""

    root: str
    dest: str
    filecount: FilecountModel
    folder: FolderModel
    filename: FilenameModel
    transfermode: TransferModeModel
    keyword: ListIncludeExcludeModel
    extension: ListIncludeExcludeModel
    filesize: MinMaxModel
    duration: MinMaxModel
    folder_size_limit: SizeLimitModel
    total_size_limit: SizeLimitModel
    options: OptionsModel

    @field_validator("root", "dest")
    @classmethod
    def is_absolute(cls, val: str) -> str:
        """Ensure root and dest paths are absolute."""
        if not os.path.isabs(val):
            return os.path.realpath(val)
        return val
