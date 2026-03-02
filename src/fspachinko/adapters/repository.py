"""Repository adapter for managing data sources."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..domain.model import FSEntry

if TYPE_CHECKING:
    import sqlite3


@dataclass(slots=True)
class AbstractFileRepository(ABC):
    """Abstract repository for managing file entries."""

    @abstractmethod
    def get(self, path: str) -> FSEntry | None:
        """Retrieve an FSEntry from the cache by its path."""

    @abstractmethod
    def add(self, entry: FSEntry) -> None:
        """Add or update an FSEntry in the cache."""


@dataclass(slots=True)
class SQLiteFileRepository:
    """Repository for managing file entries using SQLite."""

    conn: sqlite3.Connection

    def __post_init__(self) -> None:
        """Ensure the file cache table exists."""
        self._ensure_table_exists()

    def _ensure_table_exists(self) -> None:
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS file_cache (
                path TEXT PRIMARY KEY,
                stem TEXT,
                ext TEXT,
                parent TEXT,
                size INTEGER,
                mtime REAL,
                duration REAL
            )
        """)

    def get(self, path: str) -> FSEntry | None:
        """Retrieve an FSEntry from the cache by its path."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM file_cache WHERE path = ?", (path,))
        row = cursor.fetchone()
        if row:
            return FSEntry(
                path=row[0],
                stem=row[1],
                ext=row[2],
                parent=row[3],
                size=row[4],
                mtime=row[5],
                duration=row[6],
            )
        return None

    def add(self, entry: FSEntry) -> None:
        """Add or update an FSEntry in the cache."""
        self.conn.execute(
            """
            INSERT OR REPLACE INTO file_cache (path, stem, ext, parent, size, mtime, duration)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (entry.path, entry.stem, entry.ext, entry.parent, entry.size, entry.mtime, entry.duration),
        )
