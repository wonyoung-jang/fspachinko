"""Timestamp related functionality."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import ClassVar, Self


@dataclass(slots=True)
class DateTimeSingleton:
    """Singleton for current date and time."""

    now: datetime = field(init=False)
    date: str = field(init=False)
    time: str = field(init=False)
    date_time: str = field(init=False)
    instance: ClassVar[DateTimeSingleton]

    def __new__(cls) -> Self:
        """Ensure only one instance exists."""
        if not hasattr(cls, "instance"):
            cls.instance = super().__new__(cls)
        return cls.instance

    def __post_init__(self) -> None:
        """Initialize formatted date and time strings."""
        self.refresh()

    def refresh(self) -> None:
        """Refresh the current date and time."""
        self.now = datetime.now(tz=UTC)
        self.date = self.now.strftime("%Y-%m-%d")
        self.time = self.now.strftime("%H-%M-%S")
        self.date_time = f"{self.date}--{self.time}"
