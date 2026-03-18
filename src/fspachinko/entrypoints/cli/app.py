"""CLI package."""

import logging

from cyclopts import App

from fspachinko.adapters.filesystemport import get_config_path
from fspachinko.bootstrap import bootstrap, build_pipeline
from fspachinko.configuration.model import ConfigModel
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
    m = ConfigModel.from_json_path(config_path)
    pipeline = build_pipeline(m)
    bus = bootstrap(m=m, pipeline=pipeline)

    logger.debug("Process started: dir_count=%s", m.directory.count)

    for _ in range(m.directory.count):
        target_qty = pipeline.filecount_fn()
        dest_dir = pipeline.get_currdir_dest()

        logger.debug("Processing directory: %s, target_qty=%s", dest_dir, target_qty)

        start_process_cmd = ProcessDirectory(dest_dir, target_qty=target_qty)
        bus.handle(start_process_cmd)

    logger.debug("Process stopped.")
