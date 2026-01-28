"""CLI observer."""

import logging

from ..utils import FileRouletteObserver

logger = logging.getLogger(__name__)


class ConsoleObserver(FileRouletteObserver):
    """A simple console observer for File Roulette."""

    def on_progress_total(self, maximum: int) -> None:
        """Handle starting total progress."""
        logger.info("Starting total progress: %d folder(s)", maximum)

    def on_count_total(self) -> None:
        """Handle total progress count update."""
        logger.info("Total progress updated.")

    def on_progress(self, maximum: int) -> None:
        """Handle starting folder progress."""
        logger.info("Starting folder: %d file(s)", maximum)

    def on_finished(self) -> None:
        """Handle finishing process."""
        logger.info("Processing finished.")

    def on_log(self, msg: str) -> None:
        """Handle log message."""
        logger.info("%s", msg)

    def on_time(self) -> None:
        """Handle time update."""

    def on_count(self, count: int) -> None:
        """Handle folder progress count update."""
