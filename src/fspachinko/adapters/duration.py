"""Adapter for media duration/length operations."""

import logging
import shutil
import subprocess
from functools import cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)

FFPROBE_DURATION_CMD = [
    "ffprobe",
    "-v",
    "error",
    "-show_entries",
    "format=duration",
    "-of",
    "default=noprint_wrappers=1:nokey=1",
]
TIMEOUT = 2


@cache
def _get_duration_ffprobe(path: str) -> float:
    """Get the duration of a media file."""
    try:
        result = subprocess.run(
            args=[*FFPROBE_DURATION_CMD, path],
            timeout=TIMEOUT,
            capture_output=True,
            check=True,
            encoding="utf-8",
        )
        dur = float(result.stdout.strip())
    except ValueError, subprocess.SubprocessError:
        logger.debug("Unexpected error while getting duration for %s", path)
        dur = float("inf")
    return dur


@cache
def duration_fn_factory() -> Callable[[str], float]:
    """Create a get_duration function based on ffprobe availability."""
    if not shutil.which("ffprobe"):
        logger.warning("ffprobe not found in system PATH. Cannot evaluate media duration.")
        return lambda _: float("inf")
    return _get_duration_ffprobe
