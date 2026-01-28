"""Constants for file-roulette."""

import os
from enum import IntEnum, StrEnum

from .paths import Paths

# Ensure necessary directories exist
os.makedirs(Paths.profiles, exist_ok=True)

# General constants
WALKER_CACHE_LIMIT = 1000
PERCENTAGE_100 = 100.0
INVALID_FILENAME_CHARS = set(r'\/:*?"<>|')
TRUE_STRS = {"y", "yes", "t", "true", "on", "1"}
FALSE_STRS = {"n", "no", "f", "false", "off", "0"}


class DefaultPath(StrEnum):
    """Enumeration for default configuration filenames."""

    CONFIG = "file-roulette.json"
    LOGGING = "logging.json"


class ReStrFmt(StrEnum):
    """Enumeration for regex string formats."""

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
    MOVE = "Move"
    SYMLINK = "Symlink"
    HARDLINK = "Hardlink"


class AppSettings(StrEnum):
    """Enumeration for different settings categories."""

    ORGANIZATION = "Wonyoung Jang"
    DOMAIN = "wonyoungjang.org"
    APPLICATION = "File Roulette"


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


class FilenameTemplateMapKeys(StrEnum):
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
    BROWSE = "add_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"
    OPEN_DIR = "folder_open_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"
    REMOVE = "remove_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"
