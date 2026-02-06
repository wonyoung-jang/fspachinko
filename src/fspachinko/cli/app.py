"""CLI package."""

import logging
import os

from cyclopts import App

from ..config import ConfigModel
from ..config.converter import config_to_profile_file, profile_to_config_file
from ..core import build_engine
from ..utils import DefaultPath, get_config
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
        config = get_config(DefaultPath.CONFIG)

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


@app.command
def profile_to_config(profile: str, output: str) -> None:
    """Convert a GUI profile JSON to a fspachinko config JSON."""
    if not os.path.exists(profile):
        logger.error("Profile file not found: %s", profile)
        return

    profile_to_config_file(profile, output)


@app.command
def config_to_profile(config: str, output: str) -> None:
    """Convert a fspachinko config JSON to a GUI profile JSON."""
    if not os.path.exists(config):
        logger.error("Config file not found: %s", config)
        return

    config_to_profile_file(config, output)
