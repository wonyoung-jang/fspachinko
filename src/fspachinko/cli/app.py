"""CLI package."""

import logging

from cyclopts import App

from ..builder import bootstrap
from ..core import ConfigModel, DefaultPath, get_config_path
from ..domain.commands import StartProcess

logger = logging.getLogger(__name__)
app = App(
    help="fspachinko - Random file transfer utility.",
)


@app.default
def run(config_path: str = "") -> None:
    """Run the fspachinko CLI.

    Args:
        config_path (str): Path to configuration file.

    """
    if not config_path:
        config_path = get_config_path(DefaultPath.CONFIG)

    try:
        with open(config_path, encoding="utf-8") as f:
            data = f.read()
    except FileNotFoundError:
        logger.exception("Configuration file not found: %s", config_path)
        return

    config = ConfigModel.model_validate_json(data)
    bus = bootstrap(m=config)
    bus.handle(StartProcess())
