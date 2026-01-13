"""Interfaces for Mandala core components."""

from __future__ import annotations

from typing import Protocol


class MandalaObserver(Protocol):
    """Interface for Mandala Observer."""

    def on_progress(self, maximum: int) -> None:
        """Call when starting a new progress cycle."""

    def on_finished(self) -> None:
        """Call when processing is finished."""

    def on_log(self, msg: str) -> None:
        """Call to log a message."""

    def on_time(self) -> None:
        """Call to update time remaining."""

    def on_count(self, num: int) -> None:
        """Call to update progress percentage."""
