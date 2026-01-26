"""Pydantic schemas for Mandala configuration."""

from pathlib import Path  # noqa: TC003

from pydantic import BaseModel

from ..utils import TransferMode


class FilecountModel(BaseModel):
    """Model for file count configuration."""

    count: int = 0
    rand_enabled: bool = False
    rand_min: int = 0
    rand_max: int = 0


class FolderModel(BaseModel):
    """Model for folder creation configuration."""

    create_enabled: bool = False
    unique_enabled: bool = True
    name: str = ""
    count: int = 1


class FilenameModel(BaseModel):
    """Model for file renaming."""

    template: str = "{original}"


class TransferModeModel(BaseModel):
    """Model for mode configuration."""

    transfer_mode: TransferMode = TransferMode.SYMLINK


class ListIncludeExcludeModel(BaseModel):
    """Model for list filtering."""

    include_enabled: bool = False
    exclude_enabled: bool = False
    text: tuple[str, ...] = ()


class LimitMinMaxModel(BaseModel):
    """Model for size filter."""

    enabled: bool = False
    minimum: float = 0.0
    maximum: float = 0.0


class SizeLimitModel(BaseModel):
    """Model for output folder size limits."""

    enabled: bool = False
    size_limit: float = 0.0


class OptionsModel(BaseModel):
    """Model for additional options."""

    max_per_folder: int = 0
    follow_symlinks: bool = False
    dry_run_enabled: bool = True


class MandalaConfigModel(BaseModel):
    """Model for Mandala configuration."""

    root: Path
    dest: Path
    filecount: FilecountModel
    folder: FolderModel
    filename: FilenameModel
    transfermode: TransferModeModel
    keyword: ListIncludeExcludeModel
    extension: ListIncludeExcludeModel
    filesize: LimitMinMaxModel
    duration: LimitMinMaxModel
    folder_size_limit: SizeLimitModel
    total_size_limit: SizeLimitModel
    options: OptionsModel
