"""CLI package."""

import logging

from cyclopts import App

from fspachinko.adapters.filesystemport import get_config_path
from fspachinko.bootstrap import bootstrap, setup_bus_commands
from fspachinko.configuration.repository import JSONConfigRepository
from fspachinko.constants import DefaultPath
from fspachinko.domain.commands import RunTransferJob

app = App(help="fspachinko - Random file transfer utility.")
bus = bootstrap()
default_config_path = get_config_path(DefaultPath.CONFIG)
logger = logging.getLogger(__name__)


@app.default
def run(config_path: str = default_config_path) -> None:
    """Run the fspachinko CLI.

    Args:
        config_path (str): Path to configuration file.

    """
    repo = JSONConfigRepository()
    config = repo.from_json(config_path)
    for cmd in setup_bus_commands(config):
        bus.handle(cmd)
    bus.handle(RunTransferJob())
