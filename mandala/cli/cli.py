"""CLI package for Mandala."""

from pathlib import Path
from random import Random

from cyclopts import App

from ..config.constants import DEFAULT_JSON_CONFIG
from ..config.interfaces import MandalaObserver
from ..core.config import MandalaConfig
from ..core.engine import MandalaEngine
from ..core.quota import DiversityQuota
from ..core.reporter import ReportWriter
from ..core.state import MandalaState
from ..core.validator import FileValidator
from ..core.walker import RandomFSWalker

app = App(
    help="Mandala - Random file copier.",
)


class ConsoleObserver(MandalaObserver):
    """A simple console observer for Mandala."""

    def on_progress_total(self, maximum: int) -> None:
        """Handle starting total progress."""
        print(f"Starting total progress: {maximum} folder(s)")

    def on_count_total(self) -> None:
        """Handle total progress count update."""
        print("Total progress updated.")

    def on_progress(self, maximum: int) -> None:
        """Handle starting folder progress."""
        print(f"Starting folder progress: {maximum} file(s)")

    def on_finished(self) -> None:
        """Handle finishing process."""
        print("Processing finished.")

    def on_log(self, msg: str) -> None:
        """Handle log message."""
        print(f"on_log: {msg}")

    def on_time(self) -> None:
        """Handle time update."""

    def on_count(self, count: int) -> None:
        """Handle folder progress count update."""
        print(f"on_count: {count}")


def run_cli(json_path: str = "") -> None:
    """Run the Mandala CLI application."""
    if not json_path:
        json_path = DEFAULT_JSON_CONFIG

    config = MandalaConfig.from_json(Path(json_path))
    state = MandalaState()
    reporter = ReportWriter(config, state)
    validator = FileValidator(config)
    quota = DiversityQuota(
        root=config.root,
        limit_root_folder=config.diversity.root_limit,
        limit_leaf_folder=config.diversity.leaf_limit,
    )

    sys_rand = Random()
    rng_seed = sys_rand.randint(0, 2**32 - 1)
    rng = Random(rng_seed)

    observer = ConsoleObserver()

    walker = RandomFSWalker(
        root=config.root,
        rng=rng,
        quota=quota,
        trash_empty_folders=config.trash.empty_folder,
    )

    engine = MandalaEngine(
        config=config,
        state=state,
        validator=validator,
        reporter=reporter,
        rng=rng,
        quota=quota,
        walker=walker,
    )
    engine.set_observer(observer)
    engine.start()


@app.default
def main(json_path: str = "") -> None:
    """Run the Mandala CLI."""
    run_cli(json_path)


if __name__ == "__main__":
    app()
