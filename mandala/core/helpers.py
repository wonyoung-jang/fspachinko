"""Core helpers for Mandala."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

from send2trash import send2trash

if TYPE_CHECKING:
    from pathlib import Path


def trash_path(path: Path, *, condition: bool) -> None:
    """Trash a path if the condition is met."""
    if condition:
        with contextlib.suppress(Exception):
            send2trash(path)
