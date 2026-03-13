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


def get_duration(path: str) -> float:
    """Get the duration of a media file."""
    if not shutil.which("ffprobe"):
        logger.warning("ffprobe not found in system PATH. Cannot evaluate media duration.")
        return 0.0

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
        logger.exception("ffprobe failed for %s", path)
    except subprocess.TimeoutExpired:
        logger.exception("ffprobe timed out for %s", path)
    except subprocess.SubprocessError:
        logger.exception("Unexpected error while getting duration for %s", path)
    return 0.0
