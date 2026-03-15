"""Main module."""

from PySide6.QtWidgets import QVBoxLayout

from ..constants import ByteUnit, TimeUnit
from .components import (
    BaseGroupBox,
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


class UIBuilder:
    """Main Widget Builder."""

    def __init__(self) -> None:
        """Initialize the main widget builder."""
        self.root = PathSelectorWidget("Root", "root")
        self.dest = PathSelectorWidget("Destination", "dest")
        self.filecount = FileCountWidget("File count", "filecount")
        self.dircreator = DirectoryCreateWidget("Create directories", "directory")
        self.filenamer = FilenamerWidget("Filenamer", "filenamer")
        self.dirname_filter = TextFilterWidget("Directory name", "dirname")
        self.keyword_filter = TextFilterWidget("Keyword", "keyword")
        self.extension_filter = TextFilterWidget("Extension", "extension")
        self.filesize_filter = RangeFilterWidget("File Size", "filesize", tuple(ByteUnit))
        self.duration_filter = RangeFilterWidget("Duration", "duration", tuple(TimeUnit))
        self.options = OptionsWidget("Options", "options")
        self.logging = LogWidget("logging")
        self.progress = ProgressWidget("progress")
        self.has_config: tuple[BaseGroupBox, ...] = (
            self.root,
            self.dest,
            self.filecount,
            self.dircreator,
            self.filenamer,
            self.dirname_filter,
            self.keyword_filter,
            self.extension_filter,
            self.filesize_filter,
            self.duration_filter,
            self.options,
        )

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

    @property
    def config(self) -> dict:
        """Get the current configuration from all widgets."""
        config = {}
        for w in self.has_config:
            config.update(w.config)
        return config
