"""Settings handling."""

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from os.path import exists, isfile

from .model import ConfigModel

logger = logging.getLogger(__name__)


class AbstractConfigRepository(ABC):
    """Abstract class for managing configuration profiles."""

    @abstractmethod
    def set(self, dst: str, data: dict) -> None:
        """Save configuration from a dict to the profile path."""

    @abstractmethod
    def get(self, src: str) -> dict:
        """Load configuration from the profile path and return as a dict."""


@dataclass(slots=True)
class JSONConfigRepository(AbstractConfigRepository):
    """Class for managing configuration profiles."""

    model: ConfigModel = field(default_factory=ConfigModel)

    def set(self, dst: str, data: dict) -> None:
        """Save JSON data to a file."""
        with open(dst, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def get(self, src: str) -> dict:
        """Load JSON data from a file."""
        if not (exists(src) and isfile(src)):
            return {}
        with open(src, encoding="utf-8") as f:
            return json.load(f)

    def from_dict(self, config: dict) -> ConfigModel:
        """Get the current configuration from a dictionary."""
        try:
            self.model = ConfigModel.model_validate(config)
        except Exception:
            logger.exception("Failed to get configuration from dictionary. %s", config)
            raise
        else:
            return self.model

    def from_json(self, path: str) -> ConfigModel:
        """Get the current configuration from a JSON file."""
        try:
            with open(path, encoding="utf-8") as f:
                data = f.read()
            self.model = ConfigModel.model_validate_json(data)
        except Exception:
            logger.exception("Failed to get configuration from JSON file: %s", path)
            raise
        return self.model
