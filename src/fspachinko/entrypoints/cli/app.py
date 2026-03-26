"""CLI package."""

import logging

from cyclopts import App

from fspachinko.bootstrap import FSPachinkoBootstrapper, configure_bus
from fspachinko.configuration.repository import JSONConfigRepository
from fspachinko.constants import DefaultPath
from fspachinko.datapaths import get_config_path
from fspachinko.domain.commands import RunTransferJob

default_config_path = get_config_path(DefaultPath.CONFIG)
logger = logging.getLogger(__name__)
bus = FSPachinkoBootstrapper.bootstrap()
app = App(help="fspachinko - Random file transfer utility.")


@app.default
def run(config_path: str = default_config_path) -> None:
    """Run the fspachinko CLI.

    Args:
        config_path (str): Path to configuration file.

    """
    repo = JSONConfigRepository()
    config = repo.from_json(config_path)
    configure_bus(bus, config)
    bus.handle(RunTransferJob())
