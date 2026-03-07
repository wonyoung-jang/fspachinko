"""Configuration dataclasses."""

from os.path import isabs, realpath

from pydantic import BaseModel, Field, field_validator

from .constants import FilenameTemplate, TransferMode


class FilecountModel(BaseModel):
    """Model for file count configuration."""

    count: int = Field(default=10, ge=1)
    is_rand_enabled: bool = False
    rand_min: int = Field(default=1, ge=1)
    rand_max: int = Field(default=10, ge=1)


class DirectoryModel(BaseModel):
    """Model for directory creation configuration."""

    is_enabled: bool = False
    name: str = "fsp_output"
    count: int = 1


class FilenameModel(BaseModel):
    """Model for file renaming."""

    is_enabled: bool = False
    template: str = Field(default=FilenameTemplate.ORIGINAL, min_length=1)


class TextFilterModel(BaseModel):
    """Model for list search filtering."""

    is_enabled: bool = False
    should_include: bool = True
    text: str = ""


class RangeFilterModel(BaseModel):
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
    dirname: TextFilterModel
    keyword: TextFilterModel
    extension: TextFilterModel
    filesize: RangeFilterModel
    duration: RangeFilterModel
    options: OptionsModel

    @field_validator("root", "dest")
    @classmethod
    def is_absolute(cls, val: str) -> str:
        """Ensure root and dest paths are absolute."""
        if not isabs(val):
            return realpath(val)
        return val
