"""GUI constants."""

from enum import StrEnum


class GUIAppSetting(StrEnum):
    """Enumeration for different settings categories."""

    ORGANIZATION_NAME = "Wonyoung Jang"
    ORGANIZATION_DOMAIN = "https://github.com/wonyoung-jang/fspachinko"
    APPLICATION_NAME = "fspachinko"


class GUIIconFilename(StrEnum):
    """Enumeration for icon filenames."""

    WINDOW = "windowIcon.png"
    SAVE = "save_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"
    SAVE_AS = "save_as_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"
    OPEN = "file_open_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"
    START = "play_arrow_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"
    STOP = "stop_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"
    CLOSE = "close_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"
    BROWSE = "folder_open_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"
    OPEN_DIR = "open_in_new_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"


class GUISettingsKey(StrEnum):
    """Enumeration for QSettings keys."""

    GEOMETRY = "geometry"
    STATE = "state"
    CONFIG = "config"


class GUITitle(StrEnum):
    """Enumeration for GUI window titles."""

    WINDOW = "fspachinko: Transfer random files"
    SAVE_CONFIG = "Save Configuration As"
    OPEN_CONFIG = "Open Configuration"


class GUIName(StrEnum):
    """Enumeration for GUI object names."""

    RUNMENU = "run_menu"
    FILEMENU = "file_menu"
    TOOLBAR = "toolbar"


class GUILabel(StrEnum):
    """Enumeration for GUI labels."""

    FILEMENU = "&File"
    RUNMENU = "&Run"


class GUIFileDialogFilter(StrEnum):
    """Enumeration for GUI file dialog filters."""

    JSON = "JSON Files (*.json)"
