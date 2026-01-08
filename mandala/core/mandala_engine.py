"""Mandala Engine Module."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mandala.core.config_validator import FileValidator
    from mandala.core.mandala_config import MandalaConfig
    from mandala.core.mandala_logger import MandalaLogger
    from mandala.core.mandala_state import MandalaState


@dataclass(slots=True)
class MandalaEngine:
    """Core engine class for Mandala."""

    config: MandalaConfig
    state: MandalaState
    validator: FileValidator
    logger: MandalaLogger
    stop_requested: bool = False

    def __post_init__(self) -> None:
        """Initialize the file validator after the engine is created."""

    def start(self) -> None:
        """Run the main file copying process."""
        for _ in range(self.config.num_folders):
            if self.stop_requested:
                break

            self.process_folder()

        self.stop()

    def process_folder(self) -> None:
        """Process a single folder based on the current configuration."""

    def stop(self) -> None:
        """Stop the Mandala process."""
        self.stop_requested = True
