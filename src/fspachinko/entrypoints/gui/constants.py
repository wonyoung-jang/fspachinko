"""GUI constants."""

from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


class GUIStateKey(StrEnum):
    """Enumeration for QSettings keys."""

    CONFIG = "config"
    GEOMETRY = "geometry"
    STATE = "state"


class GUITitle(StrEnum):
    """Enumeration for GUI window titles."""

    OPEN_CONFIG = "Open Configuration"
    SAVE_CONFIG = "Save Configuration As"
    WINDOW = "fspachinko: Transfer random files"


FILE_DIALOG_JSON_FILTER: str = "JSON Files (*.json)"
ACTION_CONFIG: dict[str, Sequence[str]] = {
    "save": ("&Save Configuration", "Save current configuration (Ctrl+S)"),
    "save_as": ("Save Configuration &As", "Save current configuration as ... (Ctrl+Shift+S)"),
    "load": ("&Load Configuration", "Load configuration (Ctrl+O)"),
    "exit": ("&Exit", "Exit application (Ctrl+W)"),
    "start": ("&Start", "Start (Ctrl+R)"),
    "stop": ("S&top", "Stop (ESC)"),
}
MENU_CONFIG: dict[str, Sequence[str | None]] = {
    "&File": ("save", "save_as", "load", None, "exit"),
    "&Run": ("start", "stop"),
}
TOOLBAR_NAME: str = "Toolbar"
TOOLBAR_CONFIG: Sequence[str | None] = ("save", "save_as", "load", None, "start", "stop", None, "exit")
ICON_CONFIG: dict[str, str] = {
    "window": "windowIcon.png",
    "browse": "folder_open_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg",
    "open_dir": "open_in_new_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg",
    "save": "save_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg",
    "save_as": "save_as_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg",
    "load": "file_open_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg",
    "exit": "close_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg",
    "start": "play_arrow_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg",
    "stop": "stop_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg",
}
SHORTCUT_CONFIG: dict[str, str] = {
    "save": "Ctrl+S",
    "save_as": "Ctrl+Shift+S",
    "load": "Ctrl+O",
    "exit": "Ctrl+W",
    "start": "Ctrl+R",
    "stop": "ESC",
}
