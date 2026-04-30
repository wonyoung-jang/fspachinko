"""SQLite-based incremental filesystem cache."""

import sqlite3
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

    from fspachinko.domain.model import FSEntry


class AbstractMetadataCache(ABC):
    """Abstract cache manager."""

    @abstractmethod
    def get_duration(self, e: FSEntry) -> float | None: ...

    @abstractmethod
    def set_entries(self, entries: Iterable[FSEntry]) -> None: ...


@dataclass(slots=True)
class SQLiteMetadataCache(AbstractMetadataCache):
    """Filesystem cache manager."""

    path: str
    _conn: sqlite3.Connection = field(init=False)

    def __post_init__(self) -> None:
        """Initialize the cache by connecting to the SQLite database."""
        self._conn = sqlite3.connect(
            database=self.path,
            timeout=10.0,
            check_same_thread=False,
            autocommit=False,
        )
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the database schema."""
        self._conn.executescript("COMMIT; PRAGMA journal_mode=WAL")
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS files (
                path TEXT PRIMARY KEY,
                stem TEXT,
                ext TEXT,
                parent TEXT,
                size INTEGER NOT NULL,
                mtime INTEGER NOT NULL,
                duration REAL NOT NULL
            )
            """
        )

    def get_duration(self, e: FSEntry) -> float | None:
        """Return the cached duration for the given FSEntry."""
        row = self._conn.execute(
            """
            SELECT duration FROM files
            WHERE path=:path AND mtime=:mtime AND size=:size
            """,
            e.id_key,
        ).fetchone()
        return row[0] if row else None

    def set_entries(self, entries: Iterable[FSEntry]) -> None:
        """Insert many entries into cache."""
        self._conn.executemany(
            """
            INSERT INTO files (path, stem, ext, parent, size, mtime, duration)
            VALUES (:path, :stem, :ext, :parent, :size, :mtime, :duration)
            ON CONFLICT(path) DO UPDATE SET
                size=excluded.size,
                mtime=excluded.mtime,
                duration=excluded.duration
            """,
            (e.as_dict for e in entries),
        )
