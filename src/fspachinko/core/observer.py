"""Abstract interface for Observer pattern."""

from abc import ABC, abstractmethod


class Observer(ABC):
    """Interface for Observer."""

    @abstractmethod
    def on_total_start(self, maximum: int) -> None:
        """Call when starting a new total progress cycle."""

    @abstractmethod
    def on_directory_increment(self, count: int) -> None:
        """Call to update total progress percentage."""

    @abstractmethod
    def on_directory_start(self, maximum: int) -> None:
        """Call when starting a new progress cycle."""

    @abstractmethod
    def on_file_increment(self, count: int) -> None:
        """Call to update progress percentage."""

    @abstractmethod
    def on_finished(self) -> None:
        """Call when processing is finished."""
