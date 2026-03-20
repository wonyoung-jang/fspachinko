"""CLI package."""

import logging

from cyclopts import App

from fspachinko.adapters.filesystemport import get_config_path
from fspachinko.bootstrap import FSPachinkoBootstrapper, setup_bus
from fspachinko.configuration.repository import JSONConfigRepository
from fspachinko.constants import DefaultPath
from fspachinko.domain.commands import ProcessDirectory

logger = logging.getLogger(__name__)
app = App(help="fspachinko - Random file transfer utility.")
default_config_path = get_config_path(DefaultPath.CONFIG)


@app.default
def run(config_path: str = default_config_path) -> None:
    """Run the fspachinko CLI.

    Args:
        config_path (str): Path to configuration file.

    """
    repo = JSONConfigRepository()
    config = repo.model_from_json_path(config_path)
    bootstrapper = FSPachinkoBootstrapper()
    bus, pipeline = bootstrapper.bus, bootstrapper.fs_uow.pipeline
    setup_bus(bus, config)
    logger.debug("Process started: dir_count=%s", config.directory.count)
    for _ in range(config.directory.count):
        target_qty = pipeline.filecount_fn()
        dest_dir = pipeline.get_currdir_dest()
        logger.debug("Processing directory: %s, target_qty=%s", dest_dir, target_qty)
        start_process_cmd = ProcessDirectory(dest_dir, target_qty=target_qty)
        bus.handle(start_process_cmd)
    logger.debug("Process stopped.")
