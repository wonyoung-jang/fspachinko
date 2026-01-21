"""Pydantic schemas for Mandala configuration."""

from pathlib import Path

from pydantic import BaseModel

from ..utils.constants import TransferMode


class FilecountModel(BaseModel):
    """Model for file count configuration."""

    count: int = 0
    is_rand: bool = False
    min_rand: int = 0
    max_rand: int = 0


class FolderModel(BaseModel):
    """Model for folder creation configuration."""

    create: bool = False
    unique: bool = True
    name: str = ""
    count: int = 1


class FilenameModel(BaseModel):
    """Model for file renaming."""

    template: str = "{original}"


class TransferModeModel(BaseModel):
    """Model for mode configuration."""

    trash_empty_folder: bool = False
    transfer_mode: TransferMode = TransferMode.COPY
    dry_run: bool = False


class ListIncludeExcludeModel(BaseModel):
    """Model for list filtering."""

    include: bool = False
    exclude: bool = False
    text: tuple[str, ...] = ()


class LimitMinMaxModel(BaseModel):
    """Model for size filter."""

    limit: bool = False
    minimum: float = 0.0
    maximum: float = 0.0


class DiversityModel(BaseModel):
    """Model for diversity quota configuration."""

    max_per_folder: int = 0


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
    diversity: DiversityModel
