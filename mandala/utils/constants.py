"""Constants for mandala."""

from __future__ import annotations

from enum import IntEnum, StrEnum

DEFAULT_JSON_CONFIG = "mandala/mandala.json"
DEFAULT_PROFILE_DIR = ".profiles/"


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
    APPLICATION = "Mandala"


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
