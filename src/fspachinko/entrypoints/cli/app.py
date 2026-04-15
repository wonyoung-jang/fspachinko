"""CLI package."""

import logging

from cyclopts import App

from fspachinko.bootstrap import Bootstrapper
from fspachinko.config import ConfigModel
from fspachinko.datapaths import get_config_path
from fspachinko.domain.commands import ConfigurePipeline, RunTransferJob
from fspachinko.fp import Fp

default_config_path = get_config_path(Fp.Paths.CONFIG)
logger = logging.getLogger(__name__)
bootstrapper = Bootstrapper()
bus = bootstrapper.build_message_bus()
bootstrapper.logger.add_cli_log_handler()
app = App(help="fspachinko - Random file transfer utility.")


@app.default
def run(config_path: str = default_config_path) -> None:
    """Run the fspachinko CLI.

    Args:
        config_path (str): Path to configuration file.

    """
    with open(config_path, "rb") as f:
        config = ConfigModel.model_validate_json(f.read())
    bus.handle(ConfigurePipeline(config=config))
    bus.handle(
        RunTransferJob(
            root=config.root.path,
            max_per_dir=config.options.max_per_dir,
        )
    )
