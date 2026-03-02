"""Unit of Work."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Self

if TYPE_CHECKING:
    from collections.abc import Iterator

    from ..domain.events import Event
    from ..domain.model import Engine


@dataclass(slots=True)
class AbstractUnitOfWork(ABC):
    """Abstract Unit of Work."""

    engine: Engine

    def __enter__(self) -> Self:
        """Enter the runtime context related to this object."""
        return self

    def __exit__(self, *args: object) -> None:
        """Exit the runtime context related to this object."""
        self.rollback()

    def commit(self) -> None:
        """Commit the transaction."""
        self._commit()

    def yield_new_events(self) -> Iterator[Event]:
        """Collect new events generated during the transaction."""
        while self.engine.events:
            yield self.engine.events.popleft()

    @abstractmethod
    def _commit(self) -> None:
        """Commit the transaction."""

    @abstractmethod
    def rollback(self) -> None:
        """Rollback the transaction."""


@dataclass(slots=True)
class InMemoryUnitOfWork(AbstractUnitOfWork):
    """In-memory implementation of the Unit of Work pattern."""

    def __enter__(self) -> Self:
        """Enter the runtime context related to this object."""
        return super().__enter__()

    def __exit__(self, *args: object) -> None:
        """Exit the runtime context related to this object."""
        super().__exit__(*args)
        self.rollback()

    def _commit(self) -> None:
        """Commit the transaction."""
        return

    def rollback(self) -> None:
        """Rollback the transaction."""
        return
