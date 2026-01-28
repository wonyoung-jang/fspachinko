"""CLI package for Mandala."""

import logging

from cyclopts import App

from ..config import MandalaConfigModel
from ..core import build_engine
from ..utils import MandalaObserver, Paths, initialize_logging

logger = logging.getLogger(__name__)
app = App(
    help="Mandala - Random file copier.",
)


class ConsoleObserver(MandalaObserver):
    """A simple console observer for Mandala."""

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
    """Run the Mandala CLI application."""
    if not path:
        path = Paths.config("mandala.json")

    try:
        with open(path, encoding="utf-8") as f:
            data = f.read()
    except FileNotFoundError:
        logger.exception("Configuration file not found: %s", path)
        return

    observer = ConsoleObserver()
    config = MandalaConfigModel.model_validate_json(data)
    engine = build_engine(config)
    engine.set_observer(observer)
    engine.start()


@app.default
def run(path: str = "") -> None:
    """Run the Mandala CLI."""
    run_cli(path)


def main() -> None:
    """Enter Mandala CLI."""
    initialize_logging()
    logger.info("Start: Mandala GUI")
    app()
