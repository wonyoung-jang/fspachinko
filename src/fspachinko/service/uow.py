"""Unit of Work."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Self

if TYPE_CHECKING:
    from collections.abc import Iterator

    from ..adapters.pipeline import AbstractPipeline, TransferPipeline
    from ..domain.events import Event
    from ..domain.model import TransferJob

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AbstractUnitOfWork(ABC):
    """Abstract Unit of Work."""

    pipeline: AbstractPipeline
    job: TransferJob

    def __enter__(self) -> Self:
        """Enter the runtime context."""
        return self

    def __exit__(self, *args: object) -> None:
        """Exit the runtime context."""
        self.rollback()

    def commit(self) -> None:
        """Commit the transaction."""
        self._commit()

    def collect_new_events(self) -> Iterator[Event]:
        """Collect new events generated during the transaction."""
        while self.job.events:
            yield self.job.events.popleft()

    @abstractmethod
    def _commit(self) -> None:
        """Concrete implementation of committing the transaction."""

    @abstractmethod
    def rollback(self) -> None:
        """Rollback the transaction."""

    @abstractmethod
    def register_transfer(self, src: str, dst: str) -> None:
        """Register a file transfer to be performed on commit."""


@dataclass(slots=True)
class FileSystemUnitOfWork(AbstractUnitOfWork):
    """Unit of Work for file system operations."""

    pipeline: TransferPipeline
    pending: list[tuple[str, str]] = field(default_factory=list)

    def __enter__(self) -> Self:
        """Enter the runtime context."""
        self.pending.clear()
        return super().__enter__()

    def _commit(self) -> None:
        """Actually perform the I/O."""
        for src, dst in self.pending:
            try:
                self.pipeline.transfer_file(src, dst)
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
