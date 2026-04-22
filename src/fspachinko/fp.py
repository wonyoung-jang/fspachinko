"""Module for the FSP namespace for various identifiers in a namespace."""

from enum import StrEnum
from typing import ClassVar

import fspachinko


class Fp:
    """Namespace for various identifiers in a namespace."""

    INVALID_FILENAME_CHARS: frozenset[str] = frozenset(("\\", "/", ":", "*", "?", '"', "<", ">", "|"))
    MAXCHUNK = 32
    MAXFLOAT = float("inf")
    MAXINT = 2**31 - 1
    SIZE_MAP: ClassVar[dict[str, int]] = {
        "B": 1,
        "KB": 1 << 10,
        "MB": 1 << 20,
        "GB": 1 << 30,
    }
    TIME_MAP: ClassVar[dict[str, int]] = {
        "s": 1,
        "m": 60,
        "h": 3600,
    }

    class FilenameTemplate(StrEnum):
        """Enumeration for filename templates."""

        INDEX = "{index}"
        ORIGINAL = "{original}"
        PARENT = "{parent}"
        PARENTS_TO_ROOT = "{parentstoroot}"

    class FilterName(StrEnum):
        """Enumeration for filter names."""

        DIRNAME = "Directory Name Filter"
        DURATION = "Duration Filter"
        EXTENSION = "Extension Filter"
        FILESIZE = "File Size Filter"
        KEYWORD = "Keyword Filter"

    class LogData(StrEnum):
        """Enum for log data."""

        NAME = "fspachinko"

    class LogFmt(StrEnum):
        """Enum for log formats."""

        DEFAULT = "[%(asctime)s] %(levelname)s[%(module)s] %(message)s"
        DEST = "[%(asctime)s] %(message)s"

    class Path(StrEnum):
        """Enumeration for default configuration filenames."""

        APP = fspachinko.__file__
        CACHE = "fspachinko_cache.db"
        CACHE_DIR = "cache"
        CONFIG = "fspachinko.json"
        CONFIG_DIR = "configs"
        DATA_DIR = "_data"
        ICON_DIR = "icons"
        LOG_DIR = "logs"
        LOG_FILE = "fspachinko.log"

    class ReStrFmt(StrEnum):
        """Enumeration for regex string formats."""

        DIRECTORY = r"(.*){}(.*)"
        EXTENSION = r"{}$"
        KEYWORD = r"(.*){}(.*)"

    class StateStatus(StrEnum):
        """Enumeration for engine state statuses."""

        ALL_FILES_SEARCHED = "ALL FILES SEARCHED"
        NO_FILES_FOUND_ALL_SEARCHED_FOLDER_DELETED = "NO FILES FOUND | ALL FILES SEARCHED | FOLDER DELETED"
        NO_FILES_FOUND_FOLDER_DELETED = "NO FILES FOUND | FOLDER DELETED"
        SUCCESS = "SUCCESS"
        UNDEFINED = "UNDEFINED"
        USER_STOPPED = "USER STOPPED"

    class TransferMode(StrEnum):
        """Enumeration for file transfer modes."""

        COPY = "Copy"
        COPY_PRESERVE = "Copy (Preserve)"
        DRY_RUN = "Dry Run"
        HARDLINK = "Hardlink"
        MOVE = "Move"
        SYMLINK = "Symlink"

    class ConfigName(StrEnum):
        """Enumeration for configuration names."""

        DEST = "dest"
        DIRECTORY = "directory"
        DIRNAME = "dirname"
        DURATION = "duration"
        EXTENSION = "extension"
        FILECOUNT = "filecount"
        FILENAME = "filename"
        FILESIZE = "filesize"
        KEYWORD = "keyword"
        OPTIONS = "options"
        ROOT = "root"
