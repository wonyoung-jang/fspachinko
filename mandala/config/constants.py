"""Constants for mandala."""

from __future__ import annotations

from enum import StrEnum

BYTE_TO_MEGABYTE = 9.53674316406 * 10 ** (-7)
BYTE_TO_GIGABYTE = 9.31322575 * 10 ** (-10)

BYTES_IN_KILOBYTE = 1 << 10
BYTES_IN_MEGABYTE = 1 << 20
BYTES_IN_GIGABYTE = 1 << 30

SECONDS_IN_MINUTE = 60

NOWRAP = '<p style="white-space:pre">'


class SettingsEnum(StrEnum):
    """Enumeration for different settings categories."""

    ORGANIZATION = "Wonyoung Jang"
    DOMAIN = "wonyoungjang.org"
    APPLICATION = "Mandala"
