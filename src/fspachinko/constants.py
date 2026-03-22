"""Constants."""

from enum import IntEnum, StrEnum

import fspachinko

# General constants
INVALID_FILENAME_CHARS: set[str] = set(r'\/:*?"<>|')


class DefaultPath(StrEnum):
    """Enumeration for default configuration filenames."""

    APP = fspachinko.__file__
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
    EXTENSION = r"{}$"


class OSCrossError(IntEnum):
    """Enumeration for file error codes."""

    WINDOWS = 17
    UNIX = 18


class TransferMode(StrEnum):
    """Enumeration for file transfer modes."""

    DRY_RUN = "Dry Run"
    COPY = "Copy"
    COPY_PRESERVE = "Copy (Preserve)"
    MOVE = "Move"
    SYMLINK = "Symlink"
    HARDLINK = "Hardlink"


SIZE_MAP: dict[str, int] = {
    "B": 1,
    "KB": 1 << 10,
    "MB": 1 << 20,
    "GB": 1 << 30,
}

TIME_MAP: dict[str, int] = {
    "s": 1,
    "m": 60,
    "h": 3600,
}


class FilenameTemplate(StrEnum):
    """Enumeration for filename templates."""

    ORIGINAL = "{original}"
    INDEX = "{index}"
    PARENT = "{parent}"
    PARENTS_TO_ROOT = "{parentstoroot}"


class StateStatus(StrEnum):
    """Enumeration for engine state statuses."""

    UNDEFINED = "UNDEFINED"
    USER_STOPPED = "USER STOPPED"
    SUCCESS = "SUCCESS"
    ALL_FILES_SEARCHED = "ALL FILES SEARCHED"
    NO_FILES_FOUND_ALL_SEARCHED_FOLDER_DELETED = "NO FILES FOUND | ALL FILES SEARCHED | FOLDER DELETED"
    NO_FILES_FOUND_FOLDER_DELETED = "NO FILES FOUND | FOLDER DELETED"


class FilterName(StrEnum):
    """Enumeration for filter names."""

    DIRNAME = "Directory Name Filter"
    KEYWORD = "Keyword Filter"
    EXTENSION = "Extension Filter"
    FILESIZE = "File Size Filter"
    DURATION = "Duration Filter"
