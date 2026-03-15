"""Main module."""

from PySide6.QtWidgets import QVBoxLayout, QWidget

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
        self.directory = DirectoryCreateWidget("Create directories", "directory")
        self.filename = FilenamerWidget("Filenamer", "filenamer")
        self.dirname = TextFilterWidget("Directory name", "dirname")
        self.keyword = TextFilterWidget("Keyword", "keyword")
        self.extension = TextFilterWidget("Extension", "extension")
        self.filesize = RangeFilterWidget("File Size", "filesize", tuple(ByteUnit))
        self.duration = RangeFilterWidget("Duration", "duration", tuple(TimeUnit))
        self.options = OptionsWidget("Options", "options")
        self.logging = LogWidget("logging")
        self.progress = ProgressWidget("progress")
        self.all_widgets: tuple[QWidget, ...] = (
            self.root,
            self.dest,
            self.filecount,
            self.directory,
            self.filename,
            self.dirname,
            self.keyword,
            self.extension,
            self.filesize,
            self.duration,
            self.options,
            self.logging,
            self.progress,
        )
        self.has_config: tuple[BaseGroupBox, ...] = tuple(w for w in self.all_widgets if isinstance(w, BaseGroupBox))

    def build(self) -> QVBoxLayout:
        """Set up the main UI layouts."""
        layout = QVBoxLayout()
        for w in self.all_widgets:
            layout.addWidget(w)
        return layout

    @property
    def config(self) -> dict:
        """Get the current configuration from all widgets."""
        config = {}
        for w in self.has_config:
            config.update(w.config)
        return config
