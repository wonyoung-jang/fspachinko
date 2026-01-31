"""CLI package for File Roulette."""

import logging

from cyclopts import App

from ..config import ConfigModel
from ..core import build_engine
from ..utils import DefaultPath, Paths, initialize_logging
from .observer import ConsoleObserver

logger = logging.getLogger(__name__)
app = App(
    help="File Roulette - Random file transfer utility.",
)


@app.default
def run(config: str = "") -> None:
    """Run the File Roulette CLI.

    Args:
        config (str): Path to configuration file.

    """
    if not config:
        config = Paths.config(DefaultPath.CONFIG)

    try:
        with open(config, encoding="utf-8") as f:
            data = f.read()
    except FileNotFoundError:
        logger.exception("Configuration file not found: %s", config)
        return

    observer = ConsoleObserver()
    config_model = ConfigModel.model_validate_json(data)
    engine = build_engine(config_model)
    engine.set_observer(observer)
    engine.start()


def main() -> None:
    """Enter File Roulette CLI."""
    initialize_logging()
    logger.info("Start: File Roulette GUI")
    app()
