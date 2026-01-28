"""CLI package for File Roulette."""

import logging

from cyclopts import App

from ..config import FileRouletteConfigModel
from ..core import build_engine
from ..utils import DefaultPath, FileRouletteObserver, Paths, initialize_logging

logger = logging.getLogger(__name__)
app = App(
    help="File Roulette - Random file copier.",
)


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


def run_cli(path: str = "") -> None:
    """Run the File Roulette CLI application."""
    if not path:
        path = Paths.config(DefaultPath.CONFIG)

    try:
        with open(path, encoding="utf-8") as f:
            data = f.read()
    except FileNotFoundError:
        logger.exception("Configuration file not found: %s", path)
        return

    observer = ConsoleObserver()
    config = FileRouletteConfigModel.model_validate_json(data)
    engine = build_engine(config)
    engine.set_observer(observer)
    engine.start()


@app.default
def run(path: str = "") -> None:
    """Run the File Roulette CLI."""
    run_cli(path)


def main() -> None:
    """Enter File Roulette CLI."""
    initialize_logging()
    logger.info("Start: File Roulette GUI")
    app()
