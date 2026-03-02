"""Unit of Work."""

import sqlite3
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Self

from ..adapters.repository import SQLiteFileRepository

if TYPE_CHECKING:
    from collections.abc import Iterator

    from ..adapters.filesystemport import AbstractFilesystemPort
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


@dataclass(slots=True)
class SqliteUnitOfWork(AbstractUnitOfWork):
    """SQLite implementation of the Unit of Work pattern."""

    db_path: str
    fs: AbstractFilesystemPort
    tracked_dirs: list[str] = field(default_factory=list)

    def __enter__(self) -> Self:
        """Enter the runtime context related to this object."""
        self.conn = sqlite3.connect(self.db_path)
        self.files = SQLiteFileRepository(self.conn)
        self._committed = False
        return super().__enter__()

    def __exit__(self, *args: object) -> None:
        """Exit the runtime context related to this object."""
        super().__exit__(*args)
        self.conn.close()

    def register_directory(self, path: str) -> None:
        """Register a directory to be tracked for potential cleanup."""
        self.tracked_dirs.append(path)

    def _commit(self) -> None:
        self._committed = True
        self.conn.commit()

    def rollback(self) -> None:
        """Rollback the transaction."""
        self.conn.rollback()
        # If we crashed or found 0 files, wipe the physical directories we created
        if not self._committed:
            for d in self.tracked_dirs:
                self.fs.remove_directory(d)
