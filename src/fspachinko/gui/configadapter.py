"""Config adapter for the GUI."""

import logging
from typing import TYPE_CHECKING

from ..config import (
    ConfigModel,
    DirectoryModel,
    FilecountModel,
    FilenameModel,
    OptionsModel,
    RangeFilterModel,
    TextFilterModel,
)

if TYPE_CHECKING:
    from .uibuilder import UIBuilder

logger = logging.getLogger(__name__)


def get_config(ui: UIBuilder) -> ConfigModel:
    """Get the current configuration from all widgets."""
    try:
        return ConfigModel(
            root=ui.root.config,
            dest=ui.dest.config,
            filecount=FilecountModel(**ui.filecount.config),
            directory=DirectoryModel(**ui.dircreator.config),
            filename=FilenameModel(**ui.filenamer.config),
            dirname=TextFilterModel(**ui.dirname_filter.config),
            keyword=TextFilterModel(**ui.keyword_filter.config),
            extension=TextFilterModel(**ui.extension_filter.config),
            filesize=RangeFilterModel(**ui.filesize_filter.config),
            duration=RangeFilterModel(**ui.duration_filter.config),
            options=OptionsModel(**ui.options.config),
        )
    except Exception:
        logger.exception("Failed to get configuration from UI.")
        raise
