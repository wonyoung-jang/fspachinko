"""Adapter for media operations."""

import logging
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
    try:
        completed_proc = subprocess.run(
            [*DURATION_CMD, path],
            timeout=TIMEOUT,
            check=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
        )
        try:
            return float(completed_proc.stdout.strip())
        except ValueError:
            logger.exception("ffprobe output could not be parsed as float: %s", completed_proc)
            return 0.0
    except subprocess.CalledProcessError:
        logger.exception("ffprobe failed")
        return 0.0
    except subprocess.TimeoutExpired:
        logger.exception("ffprobe timed out for file: %s", path)
        return 0.0
    except Exception:
        logger.exception("Unexpected error while getting duration for file: %s", path)
        return 0.0
