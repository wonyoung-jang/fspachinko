"""Main module."""

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QVBoxLayout, QWidget

from .components import (
    BaseGroupBox,
    DirectoryCreateWidget,
    FileCountWidget,
    FilenamerWidget,
    OptionsWidget,
    PathSelectorWidget,
    RangeFilterWidget,
    TextFilterWidget,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


class CentralWidget(QWidget):
    """Main widget."""

    def __init__(self, size_units: Sequence[str], dur_units: Sequence[str], transfermodes: Sequence[str]) -> None:
        """Initialize the main widget."""
        super().__init__()
        self._config_widgets: tuple[BaseGroupBox, ...] = (
            PathSelectorWidget("Root", "root"),
            PathSelectorWidget("Destination", "dest"),
            FileCountWidget("File count", "filecount"),
            DirectoryCreateWidget("Create directories", "directory"),
            FilenamerWidget("Filenamer", "filename"),
            TextFilterWidget("Directory names", "dirname"),
            TextFilterWidget("Keywords", "keyword"),
            TextFilterWidget("Extensions", "extension"),
            RangeFilterWidget("File size", "filesize", size_units),
            RangeFilterWidget("Duration", "duration", dur_units),
            OptionsWidget("Options", "options", transfermodes),
        )
        self.setLayout(QVBoxLayout())
        self.add_to_layout(*self._config_widgets)

    @property
    def config(self) -> dict:
        """Capture the current configuration from the UI."""
        config = {}
        for w in self._config_widgets:
            config.update(w.config)
        return config

    def add_to_layout(self, *widgets: QWidget) -> None:
        """Build the layout."""
        layout = self.layout()
        for w in widgets:
            layout.addWidget(w)

    def restore_config(self, config: dict) -> None:
        """Restore the configuration to the UI."""
        for w in self._config_widgets:
            w.restore(config)

    def toggle(self, *, is_enabled: bool) -> None:
        """Lock or unlock UI elements."""
        for w in self._config_widgets:
            w.setEnabled(is_enabled)
