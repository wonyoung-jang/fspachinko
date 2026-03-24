"""Unit of Work."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Self

from .repository import JSONConfigRepository

if TYPE_CHECKING:
    from .repository import AbstractConfigRepository

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AbstractConfigUnitOfWork(ABC):
    """Abstract Unit of Work."""

    repo: AbstractConfigRepository

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
    def _commit(self) -> None:
        """Concrete implementation of committing the transaction."""

    @abstractmethod
    def rollback(self) -> None:
        """Rollback the transaction."""


@dataclass(slots=True)
class JSONConfigUnitOfWork(AbstractConfigUnitOfWork):
    """Unit of Work for JSON configuration operations."""

    repo: JSONConfigRepository = field(default_factory=JSONConfigRepository)

    def _commit(self) -> None:
        """No I/O to perform for config operations."""

    def rollback(self) -> None:
        """No I/O to rollback for config operations."""
