"""Main module."""

import logging

from PySide6.QtWidgets import QVBoxLayout

from ..constants import ByteUnit, TimeUnit
from .components import (
    DirectoryCreateWidget,
    FileCountWidget,
    FilenamerWidget,
    LogWidget,
    OptionsWidget,
    PathSelectorWidget,
    ProgressWidget,
    RangeFilterWidget,
    TextFilterWidget,
)

logger = logging.getLogger(__name__)


class UIBuilder:
    """Main Widget Builder."""

    def __init__(self) -> None:
        """Initialize the main widget builder."""
        self.root = PathSelectorWidget("Root", "root")
        self.dest = PathSelectorWidget("Destination", "dest")
        self.filecount = FileCountWidget()
        self.dircreator = DirectoryCreateWidget()
        self.filenamer = FilenamerWidget()
        self.dirname_filter = TextFilterWidget("Directory name", "dirname_filter")
        self.keyword_filter = TextFilterWidget("Keyword", "keyword_filter")
        self.extension_filter = TextFilterWidget("Extension", "extension_filter")
        self.filesize_filter = RangeFilterWidget("File Size", "filesize", tuple(ByteUnit))
        self.duration_filter = RangeFilterWidget("Duration", "duration", tuple(TimeUnit))
        self.options = OptionsWidget()
        self.logging = LogWidget()
        self.progress = ProgressWidget()

    def build(self) -> QVBoxLayout:
        """Set up the main UI layouts."""
        layout = QVBoxLayout()
        layout.addWidget(self.root)
        layout.addWidget(self.dest)
        layout.addWidget(self.filecount)
        layout.addWidget(self.dircreator)
        layout.addWidget(self.filenamer)
        layout.addWidget(self.dirname_filter)
        layout.addWidget(self.keyword_filter)
        layout.addWidget(self.extension_filter)
        layout.addWidget(self.filesize_filter)
        layout.addWidget(self.duration_filter)
        layout.addWidget(self.options)
        layout.addWidget(self.logging)
        layout.addWidget(self.progress)
        return layout
