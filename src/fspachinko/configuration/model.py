"""Configuration dataclasses."""

import logging
from os.path import isabs, realpath

from pydantic import BaseModel, Field, field_validator, model_validator

from fspachinko.constants import FilenameTemplate, TransferMode

logger = logging.getLogger(__name__)


class FilecountModel(BaseModel):
    """Model for file count configuration."""

    count: int = Field(default=10, ge=1)
    is_rand_enabled: bool = False
    rand_min: int = Field(default=1, ge=1)
    rand_max: int = Field(default=10, ge=2)

    @model_validator(mode="after")
    def validate_filecount_model(self) -> FilecountModel:
        """Validate that rand_min is less than or equal to rand_max."""
        if self.rand_min > self.rand_max:
            msg = "Random minimum cannot be greater than random maximum."
            raise ValueError(msg)
        return self


class DirectoryModel(BaseModel):
    """Model for directory creation configuration."""

    is_enabled: bool = False
    name: str = "fsp_output"
    count: int = 1

    @field_validator("count")
    @classmethod
    def validate_count(cls, val: int) -> int:
        """Validate that count is at least 1."""
        if val <= 0:
            return 1
        return val

    @model_validator(mode="after")
    def validate_directory_model(self) -> DirectoryModel:
        """Validate."""
        if not self.is_enabled:
            self.count = 1
        return self


class FilenameModel(BaseModel):
    """Model for file renaming."""

    is_enabled: bool = False
    template: str = FilenameTemplate.ORIGINAL

    @field_validator("template")
    @classmethod
    def validate_template(cls, val: str) -> str:
        """Validate that the template is not empty."""
        if val.strip() == "":
            return FilenameTemplate.ORIGINAL
        return val


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

    @model_validator(mode="after")
    def validate_range_filter_model(self) -> RangeFilterModel:
        """Validate that maximum is non-negative."""
        if self.minimum > self.maximum:
            msg = "Minimum cannot be greater than maximum."
            raise ValueError(msg)
        return self

    @field_validator("minimum")
    @classmethod
    def validate_minimum(cls, val: float) -> float:
        """Validate that minimum is non-negative."""
        if val < 0:
            return 0
        return val

    @field_validator("maximum")
    @classmethod
    def validate_maximum(cls, val: float) -> float:
        """Validate that maximum is non-negative."""
        if val <= 0:
            return float("inf")
        return val


class OptionsModel(BaseModel):
    """Model for additional options."""

    transfer_mode: str = TransferMode.DRY_RUN
    max_per_dir: int | float = 0
    is_create_unique_dirs: bool = False
    should_follow_symlink: bool = False
    rng_seed: int | str | bytes | None = None

    @field_validator("max_per_dir")
    @classmethod
    def validate_max_per_dir(cls, val: float) -> int | float:
        """Validate that max_per_dir is non-negative."""
        if val <= 0:
            return float("inf")
        return val

    @field_validator("rng_seed")
    @classmethod
    def validate_rng_seed(cls, val: int | str | bytes | None) -> int | str | bytes | None:
        """Validate rng_seed."""
        if isinstance(val, str) and val == "":
            return None
        return val


class ConfigModel(BaseModel):
    """Model for configuration."""

    root: str
    dest: str
    filecount: FilecountModel = Field(default_factory=FilecountModel)
    directory: DirectoryModel = Field(default_factory=DirectoryModel)
    filename: FilenameModel = Field(default_factory=FilenameModel)
    dirname: TextFilterModel = Field(default_factory=TextFilterModel)
    keyword: TextFilterModel = Field(default_factory=TextFilterModel)
    extension: TextFilterModel = Field(default_factory=TextFilterModel)
    filesize: RangeFilterModel = Field(default_factory=RangeFilterModel)
    duration: RangeFilterModel = Field(default_factory=RangeFilterModel)
    options: OptionsModel = Field(default_factory=OptionsModel)

    @field_validator("root", "dest")
    @classmethod
    def validate_root_and_dest_paths(cls, val: str) -> str:
        """Ensure root and dest paths are absolute."""
        if not isabs(val):
            return realpath(val)
        return val

    @classmethod
    def from_dict(cls, config: dict) -> ConfigModel:
        """Get the current configuration from a dictionary."""
        try:
            return cls.model_validate(config)
        except Exception:
            logger.exception("Failed to get configuration from dictionary.")
            raise

    @classmethod
    def from_json_path(cls, path: str) -> ConfigModel:
        """Get the current configuration from a JSON file."""
        try:
            with open(path, encoding="utf-8") as f:
                data = f.read()
            return cls.model_validate_json(data)
        except Exception:
            logger.exception("Failed to get configuration from JSON file: %s", path)
            raise
