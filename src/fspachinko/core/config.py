"""Configuration dataclasses."""

from os.path import isabs, realpath

from pydantic import BaseModel, field_validator

from .constants import FilenameTemplate, TransferMode


class FilecountModel(BaseModel):
    """Model for file count configuration."""

    count: int = 10
    is_rand_enabled: bool = False
    rand_min: int = 1
    rand_max: int = 10


class DirectoryModel(BaseModel):
    """Model for directory creation configuration."""

    is_enabled: bool = False
    name: str = "fsp_output"
    count: int = 1


class FilenameModel(BaseModel):
    """Model for file renaming."""

    is_enabled: bool = False
    template: str = FilenameTemplate.ORIGINAL


class IncludeExcludeFilterModel(BaseModel):
    """Model for list search filtering."""

    is_enabled: bool = False
    should_include: bool = True
    text: str = ""


class MinMaxFilterModel(BaseModel):
    """Model for range filter."""

    is_enabled: bool = False
    minimum: float = 0.0
    maximum: float = 10.0
    unit: str = ""


class OptionsModel(BaseModel):
    """Model for additional options."""

    transfer_mode: str = TransferMode.DRY_RUN
    max_per_dir: int = 0
    is_create_unique_dirs: bool = False
    should_follow_symlink: bool = False
    rng_seed: int | str | bytes | None = None


class ConfigModel(BaseModel):
    """Model for configuration."""

    root: str
    dest: str
    filecount: FilecountModel
    directory: DirectoryModel
    filename: FilenameModel
    dirname: IncludeExcludeFilterModel
    keyword: IncludeExcludeFilterModel
    extension: IncludeExcludeFilterModel
    filesize: MinMaxFilterModel
    duration: MinMaxFilterModel
    options: OptionsModel

    @field_validator("root", "dest")
    @classmethod
    def is_absolute(cls, val: str) -> str:
        """Ensure root and dest paths are absolute."""
        if not isabs(val):
            return realpath(val)
        return val
