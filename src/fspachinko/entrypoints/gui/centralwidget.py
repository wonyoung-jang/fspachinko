"""Main module."""

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QVBoxLayout, QWidget

if TYPE_CHECKING:
    from fspachinko.entrypoints.gui.components import BaseGroupBox


class CentralWidget(QWidget):
    """Main widget."""

    def __init__(self, *config_widgets: BaseGroupBox) -> None:
        """Initialize the main widget."""
        super().__init__()
        self._config_widgets: tuple[BaseGroupBox, ...] = tuple(config_widgets)
        layout = QVBoxLayout(self)
        for w in self._config_widgets:
            layout.addWidget(w)

    @property
    def config(self) -> dict:
        """Capture the current configuration from the UI."""
        config = {}
        for w in self._config_widgets:
            config.update(w.config)
        return config

    def restore_config(self, config: dict) -> None:
        """Restore the configuration to the UI."""
        for w in self._config_widgets:
            w.restore(config)

    def toggle(self, *, is_enabled: bool) -> None:
        """Lock or unlock UI elements."""
        for w in self._config_widgets:
            w.setEnabled(is_enabled)
