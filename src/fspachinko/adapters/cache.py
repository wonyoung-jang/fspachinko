"""SQLite-based incremental filesystem cache."""

import sqlite3
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fspachinko.domain.model import FSEntry


class AbstractMetadataCache(ABC):
    """Abstract cache manager."""

    @abstractmethod
    def get_duration(self, e: FSEntry) -> float | None:
        """Return the cached duration for the given FSEntry."""

    @abstractmethod
    def set_entry(self, e: FSEntry) -> None:
        """Upsert an entry into the cache."""


@dataclass(slots=True)
class SQLiteMetadataCache(AbstractMetadataCache):
    """Filesystem cache manager."""

    path: str
    _conn: sqlite3.Connection = field(init=False)
    _write_lock: threading.Lock = field(default_factory=threading.Lock, init=False)

    def __post_init__(self) -> None:
        """Initialize the cache by connecting to the SQLite database."""
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the database schema."""
        with self._write_lock, self._conn as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    path TEXT PRIMARY KEY,
                    stem TEXT,
                    ext TEXT,
                    parent TEXT,
                    size INTEGER,
                    mtime REAL,
                    duration REAL
                )
            """)

    def get_duration(self, e: FSEntry) -> float | None:
        """Return the cached duration for the given FSEntry."""
        with self._conn as conn:
            cursor = conn.execute(
                "SELECT duration FROM files WHERE path=? AND mtime=? AND size=?",
                (e.path, e.mtime, e.size),
            )
            row = cursor.fetchone()
        return row[0] if row else None

    def set_entry(self, e: FSEntry) -> None:
        """Upsert an entry into the cache."""
        with self._write_lock, self._conn as conn:
            conn.execute(
                """
                INSERT INTO files (path, stem, ext, parent, size, mtime, duration)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    size=excluded.size,
                    mtime=excluded.mtime,
                    duration=excluded.duration
            """,
                (e.path, e.stem, e.ext, e.parent, e.size, e.mtime, e.duration),
            )
