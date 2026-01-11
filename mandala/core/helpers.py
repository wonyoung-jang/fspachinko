"""Core helpers for Mandala."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

import send2trash

if TYPE_CHECKING:
    from pathlib import Path


def trash_path(path: Path, *, condition: bool) -> None:
    """Trash a path if the condition is met."""
    if condition:
        with contextlib.suppress(Exception):
            send2trash.send2trash(path)
