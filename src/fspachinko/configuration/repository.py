"""Settings handling."""

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from os.path import exists, isfile

from .model import ConfigModel

logger = logging.getLogger(__name__)


class AbstractConfigRepository(ABC):
    """Abstract class for managing configuration."""

    @abstractmethod
    def set(self, path: str, data: dict) -> None:
        """Save configuration from a dict to the path."""

    @abstractmethod
    def json_to_dict(self, path: str) -> dict:
        """Load configuration from the path and return as a dict."""


@dataclass(slots=True)
class JSONConfigRepository(AbstractConfigRepository):
    """Class for managing configuration."""

    def set(self, path: str, data: dict) -> None:
        """Save JSON data to a file."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def json_to_dict(self, path: str) -> dict:
        """Load JSON data from a file."""
        if not (exists(path) and isfile(path)):
            return {}
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def from_dict(self, config: dict) -> ConfigModel:
        """Get the current configuration from a dictionary."""
        try:
            return ConfigModel.model_validate(config)
        except Exception:
            logger.exception("Failed to get configuration from dictionary. %s", config)
            raise

    def from_json(self, path: str) -> ConfigModel:
        """Get the current configuration from a JSON file."""
        try:
            with open(path, encoding="utf-8") as f:
                data = f.read()
            return ConfigModel.model_validate_json(data)
        except Exception:
            logger.exception("Failed to get configuration from JSON file: %s", path)
            raise
