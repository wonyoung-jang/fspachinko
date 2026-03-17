"""Main module."""

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QVBoxLayout, QWidget

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
    from collections.abc import Callable, Sequence


class CentralWidget(QWidget):
    """Main widget."""

    def __init__(self, size_units: Sequence[str], dur_units: Sequence[str], transfermodes: Sequence[str]) -> None:
        """Initialize the main widget."""
        super().__init__()
        self.logging = LogWidget()
        self.progress = ProgressWidget()
        self._config_widgets: tuple[BaseGroupBox, ...] = (
            PathSelectorWidget("Root", "root"),
            PathSelectorWidget("Destination", "dest"),
            FileCountWidget("File count", "filecount"),
            DirectoryCreateWidget("Create directories", "directory"),
            FilenamerWidget("Filenamer", "filenamer"),
            TextFilterWidget("Directory names", "dirname"),
            TextFilterWidget("Keywords", "keyword"),
            TextFilterWidget("Extensions", "extension"),
            RangeFilterWidget("File size", "filesize", size_units),
            RangeFilterWidget("Duration", "duration", dur_units),
            OptionsWidget("Options", "options", transfermodes),
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

    @property
    def file_progress_percent(self) -> int:
        """Get the current file transfer progress percentage."""
        return self.progress.file_progress_percent

    def build_layout(self) -> None:
        """Build the layout."""
        layout = QVBoxLayout(self)
        for w in (*self._config_widgets, self.logging, self.progress):
            layout.addWidget(w)

    def restore_config(self, config: dict) -> None:
        """Restore the configuration to the UI."""
        for w in self._config_widgets:
            w.restore(config)

    def toggle(self, *, is_enabled: bool) -> None:
        """Lock or unlock UI elements."""
        for w in self._config_widgets:
            w.setEnabled(is_enabled)

    def handle_start_process(self, dir_count: int) -> None:
        """Handle the start of the process."""
        self.progress.handle_start_process(dir_count)

    def handle_directory_start(self, target: int) -> None:
        """Update the directory progress bar."""
        self.progress.handle_directory_start(target)

    def handle_file_transfer(self) -> None:
        """Update the file transfer progress bar."""
        self.progress.handle_file_transfer()
