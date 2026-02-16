"""CLI observer."""

import logging

from ..core import Observer

logger = logging.getLogger(__name__)


class ConsoleObserver(Observer):
    """A simple console observer for fspachinko."""

    def on_total_start(self, maximum: int) -> None:
        """Handle starting total progress."""
        logger.info("Starting total progress: %d directories(s)", maximum)

    def on_directory_increment(self, count: int) -> None:
        """Handle total progress count update."""

    def on_directory_start(self, maximum: int) -> None:
        """Handle starting directory progress."""
        logger.info("Starting directory: %d file(s)", maximum)

    def on_file_increment(self, count: int) -> None:
        """Handle directory progress count update."""

    def on_finished(self) -> None:
        """Handle finishing process."""
        logger.info("Processing finished.")
