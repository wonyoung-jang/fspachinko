"""Protocols for File Roulette."""

from abc import ABC, abstractmethod


class FileRouletteObserver(ABC):
    """Interface for File Roulette Observer."""

    @abstractmethod
    def on_progress_total(self, maximum: int) -> None:
        """Call when starting a new total progress cycle."""

    @abstractmethod
    def on_count_total(self) -> None:
        """Call to update total progress percentage."""

    @abstractmethod
    def on_progress(self, maximum: int) -> None:
        """Call when starting a new progress cycle."""

    @abstractmethod
    def on_finished(self) -> None:
        """Call when processing is finished."""

    @abstractmethod
    def on_log(self, msg: str) -> None:
        """Call to log a message."""

    @abstractmethod
    def on_time(self) -> None:
        """Call to update time remaining."""

    @abstractmethod
    def on_count(self, count: int) -> None:
        """Call to update progress percentage."""
