"""Unit of Work."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Self

from fspachinko.adapters.repository import AbstractTransferRepository, TransferRepository

if TYPE_CHECKING:
    from collections.abc import Iterator

    from fspachinko.domain.events import Event

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AbstractTransferUnitOfWork(ABC):
    """Abstract Unit of Work."""

    repo: AbstractTransferRepository

    def __enter__(self) -> Self:
        """Enter the runtime context."""
        return self

    def __exit__(self, *args: object) -> None:
        """Exit the runtime context."""
        self.rollback()

    def commit(self) -> None:
        """Commit the transaction."""
        self._commit()

    @abstractmethod
    def collect_new_events(self) -> Iterator[Event]:
        """Collect new events that were generated during the transaction."""

    @abstractmethod
    def _commit(self) -> None:
        """Concrete implementation of committing the transaction."""

    @abstractmethod
    def rollback(self) -> None:
        """Rollback the transaction."""


@dataclass(slots=True)
class TransferUnitOfWork(AbstractTransferUnitOfWork):
    """Abstract Unit of Work."""

    repo: TransferRepository = field(default_factory=TransferRepository)

    def __enter__(self) -> Self:
        """Enter the runtime context."""
        self.repo.clear_pending()
        return super().__enter__()

    def collect_new_events(self) -> Iterator[Event]:
        """Collect new events that were generated during the transaction."""
        while events := self.repo.job.events:
            yield events.popleft()

    def _commit(self) -> None:
        """Actually perform the I/O."""
        self.repo.transfer_all()

    def rollback(self) -> None:
        """If something failed, delete the files we just wrote."""
        self.repo.clear_pending()
