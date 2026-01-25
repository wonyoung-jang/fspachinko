"""CLI package for Mandala."""

import logging
from pathlib import Path

from cyclopts import App

from ..config import MandalaConfigModel
from ..core import build_engine
from ..utils import DEFAULT_MANDALA_CONFIG_JSON, MandalaObserver, initialize_logging

logger = logging.getLogger(__name__)
app = App(
    help="Mandala - Random file copier.",
)


class ConsoleObserver(MandalaObserver):
    """A simple console observer for Mandala."""

    def on_progress_total(self, maximum: int) -> None:
        """Handle starting total progress."""
        print(f"Starting total progress: {maximum} folder(s)")

    def on_count_total(self) -> None:
        """Handle total progress count update."""
        print("Total progress updated.")

    def on_progress(self, maximum: int) -> None:
        """Handle starting folder progress."""
        print(f"Starting folder progress: {maximum} file(s)")

    def on_finished(self) -> None:
        """Handle finishing process."""
        print("Processing finished.")

    def on_log(self, msg: str) -> None:
        """Handle log message."""
        print(f"on_log: {msg}")

    def on_time(self) -> None:
        """Handle time update."""

    def on_count(self, count: int) -> None:
        """Handle folder progress count update."""
        print(f"on_count: {count}")


def run_cli(config: str = "") -> None:
    """Run the Mandala CLI application."""
    if not config:
        config = DEFAULT_MANDALA_CONFIG_JSON

    observer = ConsoleObserver()
    config = MandalaConfigModel.model_validate_json(Path(config).read_text(encoding="utf-8"))
    engine = build_engine(config)
    engine.set_observer(observer)
    engine.start()


@app.default
def run(json_path: str = "") -> None:
    """Run the Mandala CLI."""
    run_cli(json_path)


def main() -> None:
    """Enter Mandala CLI."""
    initialize_logging()
    logger.info("Start: Mandala GUI")
    app()
