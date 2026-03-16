"""Main module."""

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QVBoxLayout, QWidget

from fspachinko.adapters.filesystemport import get_available_transfer_modes
from fspachinko.constants import ByteUnit, TimeUnit

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

if TYPE_CHECKING:
    from collections.abc import Callable


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
        self.options = OptionsWidget("Options", "options", tuple(get_available_transfer_modes().keys()))
        self.logging = LogWidget()
        self.progress = ProgressWidget()
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

    @property
    def log_append(self) -> Callable:
        """Get the log append function."""
        return self.logging.append

    def handle_start_process(self, dir_count: int) -> None:
        """Handle the start of the process."""
        self.progress.handle_start_process(dir_count)

    def handle_directory_start(self, target: int) -> None:
        """Update the directory progress bar."""
        self.progress.handle_directory_start(target)

    def handle_file_transfer(self) -> int:
        """Update the file progress bar and return the current percentage."""
        return self.progress.handle_file_transfer()

    def toggle(self, *, is_enabled: bool) -> None:
        """Lock or unlock UI elements."""
        for component in self.has_config:
            component.setEnabled(is_enabled)

    def restore(self, config: dict) -> None:
        """Restore the UI to its default state."""
        for component in self.has_config:
            component.restore(config)
