"""Constants."""

from enum import IntEnum, StrEnum

# General constants
WALKER_CACHE_LIMIT: int = 1000
PERCENTAGE_100: float = 100.0
INVALID_FILENAME_CHARS: set[str] = set(r'\/:*?"<>|')
DURATION_CMD = [
    "ffprobe",
    "-v",
    "error",
    "-show_entries",
    "format=duration",
    "-of",
    "default=noprint_wrappers=1:nokey=1",
]


class DefaultPath(StrEnum):
    """Enumeration for default configuration filenames."""

    CONFIG = "fspachinko.json"
    DATA_DIR = "_data"
    ICON_DIR = "icons"
    CONFIG_DIR = "configs"
    GUI_PROFILE_DIR = "gui_profiles"
    LOG_DIR = "logs"


class ReStrFmt(StrEnum):
    """Enumeration for regex string formats."""

    DIRECTORY = r"(.*){}(.*)"
    KEYWORD = r"(.*){}(.*)"
    EXTENSION = r".{}$"


class FileError(IntEnum):
    """Enumeration for file error codes."""

    WINDOWS_CROSS_DRIVE_ERROR = 17
    UNIX_CROSS_FILESYSTEM_ERROR = 18


class SecondsIn(IntEnum):
    """Enumeration for seconds in units."""

    SECOND = 1
    MINUTE = 60
    HOUR = 3600


class BytesIn(IntEnum):
    """Enumeration for bytes in units."""

    BYTE = 1
    KILOBYTE = 1 << 10
    MEGABYTE = 1 << 20
    GIGABYTE = 1 << 30


class TransferMode(StrEnum):
    """Enumeration for file transfer modes."""

    COPY = "Copy"
    COPY_PRESERVE = "Copy (Preserve)"
    MOVE = "Move"
    SYMLINK = "Symlink"
    HARDLINK = "Hardlink"


class AppSetting(StrEnum):
    """Enumeration for different settings categories."""

    ORGANIZATION_NAME = "Wonyoung Jang"
    ORGANIZATION_DOMAIN = "https://github.com/wonyoung-jang/fspachinko"
    APPLICATION_NAME = "fspachinko"


class ByteUnit(StrEnum):
    """Enumeration for size units."""

    BYTES = "B"
    KILOBYTES = "KB"
    MEGABYTES = "MB"
    GIGABYTES = "GB"


class TimeUnit(StrEnum):
    """Enumeration for time units."""

    SECONDS = "s"
    MINUTES = "m"
    HOURS = "h"


SIZE_MAP = {
    ByteUnit.BYTES: BytesIn.BYTE,
    ByteUnit.KILOBYTES: BytesIn.KILOBYTE,
    ByteUnit.MEGABYTES: BytesIn.MEGABYTE,
    ByteUnit.GIGABYTES: BytesIn.GIGABYTE,
}

TIME_MAP = {
    TimeUnit.SECONDS: SecondsIn.SECOND,
    TimeUnit.MINUTES: SecondsIn.MINUTE,
    TimeUnit.HOURS: SecondsIn.HOUR,
}


class FilenameTemplate(StrEnum):
    """Enumeration for filename templates."""

    ORIGINAL = "{original}"
    INDEX = "{index}"
    DATE = "{date}"
    TIME = "{time}"
    DATETIME = "{datetime}"
    PARENT = "{parent}"
    PARENTS_TO_ROOT = "{parentstoroot}"


class FilenameTemplateMapKey(StrEnum):
    """Enumeration for filename templates."""

    ORIGINAL = "original"
    INDEX = "index"
    DATE = "date"
    TIME = "time"
    DATETIME = "datetime"
    PARENT = "parent"
    PARENTS_TO_ROOT = "parentstoroot"


class IconFilename(StrEnum):
    """Enumeration for icon filenames."""

    WINDOW = "windowIcon.png"
    SAVE = "save_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"
    SAVE_AS = "save_as_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"
    OPEN = "file_open_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"
    AUTOSAVE = "sync_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"
    START = "play_arrow_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"
    STOP = "stop_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"
    CLOSE = "close_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"
    BROWSE = "folder_open_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"
    OPEN_DIR = "open_in_new_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"


class DateTimeFormat(StrEnum):
    """Enumeration for date and time formats."""

    DATE = "%Y-%m-%d"
    TIME = "%H-%M-%S"
    DATETIME = "%Y-%m-%d %H:%M:%S"


class StateStatus(StrEnum):
    """Enumeration for engine state statuses."""

    USER_STOPPED = "USER STOPPED"
    SUCCESS = "SUCCESS"
    ALL_FILES_SEARCHED = "ALL FILES SEARCHED"
    NO_FILES_FOUND_ALL_SEARCHED_FOLDER_DELETED = "NO FILES FOUND | ALL FILES SEARCHED | FOLDER DELETED"
    NO_FILES_FOUND_FOLDER_DELETED = "NO FILES FOUND | FOLDER DELETED"


class GUISettingsKey(StrEnum):
    """Enumeration for QSettings keys."""

    GEOMETRY = "geometry"
    STATE = "state"
    PROFILE = "profile"


class GUITitle(StrEnum):
    """Enumeration for GUI window titles."""

    WINDOW = "fspachinko: Transfer random files"
    SAVE_PROFILE = "Save Profile As"
    OPEN_PROFILE = "Open Profile"


class GUIName(StrEnum):
    """Enumeration for GUI object names."""

    CENTRAL_WIDGET = "central_widget"
    MENUBAR = "menubar"
    RUNMENU = "run_menu"
    FILEMENU = "file_menu"
    TOOLBAR = "toolbar"
    STATUSBAR = "statusbar"


class GUILabel(StrEnum):
    """Enumeration for GUI labels."""

    FILEMENU = "&File"
    RUNMENU = "&Run"


class GUIFileDialogFilter(StrEnum):
    """Enumeration for GUI file dialog filters."""

    JSON = "JSON Files (*.json)"
