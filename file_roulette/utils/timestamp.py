"""Provider for current date and time."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import ClassVar

from .constants import DateTimeFormat


@dataclass(slots=True)
class DateTimeStamp:
    """Provider for current date and time."""

    _now: ClassVar[datetime] = datetime.now(tz=UTC)
    date: ClassVar[str] = _now.strftime(DateTimeFormat.DATE)
    time: ClassVar[str] = _now.strftime(DateTimeFormat.TIME)
    date_time: ClassVar[str] = f"{date}--{time}"
    date_time_report_str: ClassVar[str] = _now.strftime(DateTimeFormat.DATETIME)

    @classmethod
    def refresh(cls) -> None:
        """Refresh the current date and time."""
        cls._now = datetime.now(tz=UTC)
        cls.date = cls._now.strftime(DateTimeFormat.DATE)
        cls.time = cls._now.strftime(DateTimeFormat.TIME)
        cls.date_time = f"{cls.date}--{cls.time}"
        cls.date_time_report_str = cls._now.strftime(DateTimeFormat.DATETIME)
