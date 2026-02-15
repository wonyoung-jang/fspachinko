"""CLI observer."""

import logging

from ..core import Observer

logger = logging.getLogger(__name__)


class ConsoleObserver(Observer):
    """A simple console observer for fspachinko."""

    def on_progress_total(self, maximum: int) -> None:
        """Handle starting total progress."""
        logger.info("Starting total progress: %d directories(s)", maximum)

    def on_count_total(self) -> None:
        """Handle total progress count update."""
        logger.info("Total progress updated.")

    def on_progress(self, maximum: int) -> None:
        """Handle starting directory progress."""
        logger.info("Starting directory: %d file(s)", maximum)

    def on_finished(self) -> None:
        """Handle finishing process."""
        logger.info("Processing finished.")

    def on_count(self, count: int) -> None:
        """Handle directory progress count update."""
