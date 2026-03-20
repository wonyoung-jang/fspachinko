"""Unit of Work."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Self

from fspachinko.domain.model import TransferJob

if TYPE_CHECKING:
    from collections.abc import Iterator

    from fspachinko.adapters.pipeline import AbstractPipeline
    from fspachinko.domain.events import Event

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AbstractUnitOfWork(ABC):
    """Abstract Unit of Work."""

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
class FileSystemUnitOfWork(AbstractUnitOfWork):
    """Abstract Unit of Work."""

    pipeline: AbstractPipeline
    pending: list[tuple[str, str]] = field(default_factory=list)
    _job: TransferJob = field(default_factory=TransferJob)

    def __enter__(self) -> Self:
        """Enter the runtime context."""
        self.pending.clear()
        return super().__enter__()

    @property
    def job(self) -> TransferJob:
        """Get the current transfer job."""
        return self._job

    @job.setter
    def job(self, job: TransferJob) -> None:
        """Set the current transfer job."""
        self._job = job

    def collect_new_events(self) -> Iterator[Event]:
        """Collect new events that were generated during the transaction."""
        while self.job.events:
            yield self.job.events.popleft()

    def _commit(self) -> None:
        """Actually perform the I/O."""
        for src, dst in self.pending:
            try:
                self.pipeline.transfer_fn(src, dst)
            except OSError:
                logger.debug("Failed to transfer file from %s -> %s", src, dst)
                continue
        self.pending.clear()

    def rollback(self) -> None:
        """If something failed, delete the files we just wrote."""
        self.pending.clear()

    def register_transfer(self, src: str, dst: str) -> None:
        """Don't transfer yet. Just record the intent."""
        self.pending.append((src, dst))
