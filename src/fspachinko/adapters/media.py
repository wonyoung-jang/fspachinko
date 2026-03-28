"""Adapter for media operations."""

import logging
import shutil
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)

DURATION_CMD = [
    "ffprobe",
    "-v",
    "error",
    "-show_entries",
    "format=duration",
    "-of",
    "default=noprint_wrappers=1:nokey=1",
]
TIMEOUT = 2


class AbstractDurationFnManager(ABC):
    """Abstract interface for reading media duration."""

    @abstractmethod
    def get_duration(self, path: str) -> float:
        """Get the duration of a media file."""


@dataclass(slots=True)
class DurationFnManager(AbstractDurationFnManager):
    """Concrete implementation of AbstractDurationFnManager using ffprobe."""

    _get_duration: Callable[[str], float] = field(init=False)

    def __post_init__(self) -> None:
        """Check for ffprobe availability."""
        if not shutil.which("ffprobe"):
            logger.warning("ffprobe not found in system PATH. Cannot evaluate media duration.")
            self._get_duration = _get_duration_noop
        else:
            self._get_duration = _get_duration_ffprobe

    def get_duration(self, path: str) -> float:
        """Get the duration of a media file."""
        return self._get_duration(path)


def _get_duration_noop(_: str) -> float:
    """No-op function for getting media duration when ffprobe is not available."""
    return float("inf")


def _get_duration_ffprobe(path: str) -> float:
    """Get the duration of a media file."""
    try:
        completed_proc = subprocess.run(
            [*DURATION_CMD, path],
            timeout=TIMEOUT,
            check=True,
            encoding="utf-8",
            capture_output=True,
        )
        return float(completed_proc.stdout.strip())
    except ValueError:
        logger.exception("ffprobe output could not be parsed as float for %s", path)
    except subprocess.CalledProcessError:
        logger.debug("ffprobe failed for %s", path)
    except subprocess.TimeoutExpired:
        logger.debug("ffprobe timed out for %s", path)
    except subprocess.SubprocessError:
        logger.debug("Unexpected error while getting duration for %s", path)
    return float("inf")
