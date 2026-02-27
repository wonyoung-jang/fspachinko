"""CLI observer."""

import logging

from ..core import AbstractObserver

logger = logging.getLogger(__name__)


class ConsoleObserver(AbstractObserver):
    """A simple console observer for fspachinko."""

    def on_start_process(self, dir_count: int) -> None:
        """Call when starting a run of the engine."""
        logger.info("Starting process: %d directories(s)", dir_count)

    def on_directory_start(self, idx: int, target: int) -> None:
        """Call when starting to process a directory."""
        logger.info("Start directory %d: transfer %d file(s)", idx, target)

    def on_file_transferred(self, count: int) -> None:
        """Call when a file is transferred."""
        logger.debug("File %d transferred", count)

    def on_finished(self) -> None:
        """Call when processing is finished."""
        logger.info("Processing finished.")
