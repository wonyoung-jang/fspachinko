"""Repository implementations for handling data access operations."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from fspachinko.domain.model import TransferJob

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


class AbstractTransferRepository(ABC):
    """Abstract base class for repositories."""

    transfer_fn: Callable = lambda _, __: None

    @abstractmethod
    def add(self, job: TransferJob) -> None:
        """Add an item to the repository."""

    @abstractmethod
    def get(self) -> TransferJob:
        """Retrieve an item from the repository by its identifier."""

    @abstractmethod
    def add_transfer(self, src: str, dst: str) -> None:
        """Add a pending transfer to the repository."""


@dataclass(slots=True)
class TransferRepository(AbstractTransferRepository):
    """Repository for transfer jobs."""

    job: TransferJob = field(default_factory=TransferJob)
    _pending: list[tuple[str, str]] = field(default_factory=list)

    def add(self, job: TransferJob) -> None:
        """Add a transfer job to the repository."""
        self.job = job

    def get(self) -> TransferJob:
        """Retrieve a transfer job from the repository by its identifier."""
        return self.job

    def clear_pending(self) -> None:
        """Clear pending transfers."""
        self._pending.clear()

    def add_transfer(self, src: str, dst: str) -> None:
        """Add a pending transfer to the repository."""
        self._pending.append((src, dst))

    def transfer_all(self) -> None:
        """Execute all pending transfers."""
        for src, dst in self._pending:
            try:
                self.transfer_fn(src, dst)
            except OSError:
                logger.debug("Failed to transfer %s to %s", src, dst)
                continue
        self.clear_pending()
