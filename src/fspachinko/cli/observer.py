"""CLI observer."""

import logging

from ..core import Observer

logger = logging.getLogger(__name__)


class ConsoleObserver(Observer):
    """A simple console observer for fspachinko."""

    def on_start_process(self, ndir_to_create: int) -> None:
        """Call when starting a run of the engine."""
        logger.info("Starting process: %d directories(s)", ndir_to_create)

    def on_directory_start(self, idx: int, nfiles_to_process: int) -> None:
        """Call when starting to process a directory."""
        logger.info("Start directory %d: transfer %d file(s)", idx, nfiles_to_process)

    def on_file_increment(self, count: int) -> None:
        """Call when a file is processed."""
        logger.debug("File %d processed", count)

    def on_finished(self) -> None:
        """Call when processing is finished."""
        logger.info("Processing finished.")
