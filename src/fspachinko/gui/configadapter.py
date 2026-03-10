"""Config adapter for the GUI."""

import logging
from typing import TYPE_CHECKING

from ..config import ConfigModel

if TYPE_CHECKING:
    from .uibuilder import UIBuilder

logger = logging.getLogger(__name__)


def get_config(ui: UIBuilder) -> ConfigModel:
    """Get the current configuration from all widgets."""
    config_dict = {
        "root": ui.root.config,
        "dest": ui.dest.config,
        "filecount": ui.filecount.config,
        "directory": ui.dircreator.config,
        "filename": ui.filenamer.config,
        "options": ui.options.config,
        "dirname": ui.dirname_filter.config,
        "keyword": ui.keyword_filter.config,
        "extension": ui.extension_filter.config,
        "filesize": ui.filesize_filter.config,
        "duration": ui.duration_filter.config,
    }
    try:
        return ConfigModel.model_validate(config_dict)
    except Exception:
        logger.exception("Failed to get configuration from UI.")
        raise
