"""CLI package."""

import logging

from cyclopts import App

from ..core import ConfigModel, DefaultPath, build_engine, get_config_path
from .observer import ConsoleObserver

logger = logging.getLogger(__name__)
app = App(
    help="fspachinko - Random file transfer utility.",
)


@app.default
def run(config: str = "") -> None:
    """Run the fspachinko CLI.

    Args:
        config (str): Path to configuration file.

    """
    if not config:
        config = get_config_path(DefaultPath.CONFIG)

    try:
        with open(config, encoding="utf-8") as f:
            data = f.read()
    except FileNotFoundError:
        logger.exception("Configuration file not found: %s", config)
        return

    observer = ConsoleObserver()
    config_model = ConfigModel.model_validate_json(data)
    engine = build_engine(config_model)
    engine.observer = observer
    engine.start()
