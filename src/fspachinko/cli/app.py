"""CLI package."""

import logging

from cyclopts import App

from ..adapters.filesystemport import get_config_path
from ..bootstrap import bootstrap, build_pipeline
from ..config import ConfigModel
from ..constants import DefaultPath
from ..domain.commands import StartProcessingDirectory

logger = logging.getLogger(__name__)
app = App(help="fspachinko - Random file transfer utility.")
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

    m = ConfigModel.model_validate_json(data)
    pipeline = build_pipeline(m)
    bus = bootstrap(m=m, pipeline=pipeline)

    logger.debug("Process started: dir_count=%s", m.directory.count)

    for dir_idx in range(1, m.directory.count + 1):
        target_qty = pipeline.filenamer_fn()
        dest_dir = pipeline.get_currdir_dest()

        logger.debug("Processing directory: dir_idx=%s, target_qty=%s", dir_idx, target_qty)

        start_process_cmd = StartProcessingDirectory(dest_dir, target_qty=target_qty)
        bus.handle(start_process_cmd, uow=bus.uow)

    logger.debug("Process stopped.")
