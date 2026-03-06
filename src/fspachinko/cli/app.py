"""CLI package."""

import logging

from cyclopts import App

from ..bootstrap import bootstrap
from ..config import ConfigModel
from ..constants import DefaultPath
from ..datapaths import get_config_path
from ..domain.commands import StartProcess

logger = logging.getLogger(__name__)
app = App(
    help="fspachinko - Random file transfer utility.",
)
default_config_path = get_config_path(DefaultPath.CONFIG)


@app.default
def run(config_path: str = default_config_path) -> None:
    """Run the fspachinko CLI.

    Args:
        config_path (str): Path to configuration file.

    """
    try:
        with open(config_path, encoding="utf-8") as f:
            data = f.read()
    except FileNotFoundError:
        logger.exception("Configuration file not found: %s", config_path)
        return

    config = ConfigModel.model_validate_json(data)
    bus = bootstrap(m=config)
    bus.handle(StartProcess())
