"""CLI package."""

import logging

from cyclopts import App

from fspachinko.adapters.filesystemport import get_config_path
from fspachinko.bootstrap import bootstrap, setup_bus
from fspachinko.configuration.repository import JSONConfigRepository
from fspachinko.constants import DefaultPath
from fspachinko.domain.commands import ProcessDirectory

app = App(help="fspachinko - Random file transfer utility.")
bus, pipeline = bootstrap()
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
    setup_bus(bus, config)
    logger.debug("Process started: dir_count=%s", config.directory.count)
    for dest_dir, target_qty in pipeline.dest_dir_inputs:
        logger.debug("Processing directory: %s, target_qty=%s", dest_dir, target_qty)
        start_process_cmd = ProcessDirectory(dest_dir, target_qty=target_qty)
        bus.handle(start_process_cmd)
    logger.debug("Process stopped.")
