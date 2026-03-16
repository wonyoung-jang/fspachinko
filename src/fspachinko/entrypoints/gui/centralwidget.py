"""Main module."""

from typing import TYPE_CHECKING

from PySide6.QtCore import Slot
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


class CentralWidget(QWidget):
    """Main widget."""

    def __init__(self) -> None:
        """Initialize the main widget."""
        super().__init__()
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
        self._config_widgets: tuple[BaseGroupBox, ...] = (
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
        )
        self.build_layout()

    @property
    def config(self) -> dict:
        """Capture the current configuration from the UI."""
        config = {}
        for w in self._config_widgets:
            config.update(w.config)
        return config

    @property
    def log_append(self) -> Callable[[str], None]:
        """Get the log append function."""
        return self.logging.append

    def build_layout(self) -> None:
        """Build the layout."""
        layout = QVBoxLayout()
        for w in (*self._config_widgets, self.logging, self.progress):
            layout.addWidget(w)
        self.setLayout(layout)

    def restore_config(self, config: dict) -> None:
        """Restore the configuration to the UI."""
        for component in self._config_widgets:
            component.restore(config)

    @Slot(int)
    def handle_start_process(self, dir_count: int) -> None:
        """Handle the start of the process."""
        self.progress.handle_start_process(dir_count)

    @Slot(int)
    def handle_directory_start(self, target: int) -> None:
        """Update the directory progress bar."""
        self.progress.handle_directory_start(target)

    def handle_file_transfer(self) -> int:
        """Update the file transfer progress bar."""
        return self.progress.handle_file_transfer()

    def toggle(self, *, is_enabled: bool) -> None:
        """Lock or unlock UI elements."""
        for component in self._config_widgets:
            component.setEnabled(is_enabled)
