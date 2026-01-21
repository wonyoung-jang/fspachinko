"""Stylesheet loader for Mandala GUI."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

STYLESHEET_PATH = Path(__file__).parent / "style.qss"


def load_stylesheet() -> str:
    """Load the Qt stylesheet from file.

    Returns:
        str: The stylesheet content as a string, or empty string if loading fails.

    """
    try:
        return STYLESHEET_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.warning("Stylesheet file not found.")
        return ""
    except Exception:
        logger.exception("Error loading stylesheet")
        return ""
