"""Config adapter for the GUI."""

import logging
from typing import TYPE_CHECKING

from ..config import ConfigModel

if TYPE_CHECKING:
    from .uibuilder import UIBuilder

logger = logging.getLogger(__name__)


def get_config(ui: UIBuilder) -> ConfigModel:
    """Get the current configuration from all widgets."""
    try:
        return ConfigModel.model_validate(ui.config)
    except Exception:
        logger.exception("Failed to get configuration from UI.")
        raise
