"""Constants for mandala."""

from __future__ import annotations

from enum import StrEnum

BYTE_TO_MEGABYTE = 9.53674316406 * 10 ** (-7)
BYTE_TO_GIGABYTE = 9.31322575 * 10 ** (-10)

BYTES_IN_BYTE = 1
BYTES_IN_KILOBYTE = BYTES_IN_BYTE << 10
BYTES_IN_MEGABYTE = BYTES_IN_BYTE << 20
BYTES_IN_GIGABYTE = BYTES_IN_BYTE << 30

SECONDS_IN_SECOND = 1
SECONDS_IN_MINUTE = SECONDS_IN_SECOND * 60
SECONDS_IN_HOUR = SECONDS_IN_MINUTE * 60

DEFAULT_JSON_CONFIG = "mandala/mandala.json"
DEFAULT_PROFILE_DIR = ".profiles/"

# NOWRAP = '<p style="white-space:pre">'


class SettingsEnum(StrEnum):
    """Enumeration for different settings categories."""

    ORGANIZATION = "Wonyoung Jang"
    DOMAIN = "wonyoungjang.org"
    APPLICATION = "Mandala"


class SizeUnitEnum(StrEnum):
    """Enumeration for size units."""

    BYTES = "B"
    KILOBYTES = "KB"
    MEGABYTES = "MB"
    GIGABYTES = "GB"


class TimeUnitEnum(StrEnum):
    """Enumeration for time units."""

    SECONDS = "s"
    MINUTES = "m"
    HOURS = "h"


SIZE_MAP = {
    SizeUnitEnum.BYTES: BYTES_IN_BYTE,
    SizeUnitEnum.KILOBYTES: BYTES_IN_KILOBYTE,
    SizeUnitEnum.MEGABYTES: BYTES_IN_MEGABYTE,
    SizeUnitEnum.GIGABYTES: BYTES_IN_GIGABYTE,
}

TIME_MAP = {
    TimeUnitEnum.SECONDS: SECONDS_IN_SECOND,
    TimeUnitEnum.MINUTES: SECONDS_IN_MINUTE,
    TimeUnitEnum.HOURS: SECONDS_IN_HOUR,
}
