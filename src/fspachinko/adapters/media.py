"""Adapter for media operations."""

import logging
import shutil
import subprocess

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


# Determine which duration function to use based on ffprobe availability
get_duration = _get_duration_ffprobe
if not shutil.which("ffprobe"):
    logger.warning("ffprobe not found in system PATH. Cannot evaluate media duration.")
    get_duration = _get_duration_noop
