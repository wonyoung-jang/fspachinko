"""CLI package."""

import logging

from cyclopts import App

from fspachinko.bootstrap import FSPachinkoBootstrapper
from fspachinko.config import json_to_config
from fspachinko.constants import DefaultPath
from fspachinko.datapaths import get_config_path
from fspachinko.domain.commands import RunTransferJob

default_config_path = get_config_path(DefaultPath.CONFIG)
logger = logging.getLogger(__name__)
bootstrapper = FSPachinkoBootstrapper()
bus = bootstrapper.bootstrap()
bus.logger.add_cli_log_handler()
app = App(help="fspachinko - Random file transfer utility.")


@app.default
def run(config_path: str = default_config_path) -> None:
    """
    Run the fspachinko CLI.

    Args:
        config_path (str): Path to configuration file.

    """
    config = json_to_config(config_path)
    bootstrapper.configure_pipeline_for_run(config)
    bus.handle(
        RunTransferJob(
            root=config.root,
            max_per_dir=config.options.max_per_dir,
            unique_files_only=config.options.is_create_unique_dirs,
        )
    )
