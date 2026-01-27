"""Timestamp related functionality."""

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(slots=True)
class DateTimeProvider:
    """Provider for current date and time."""

    _now: datetime = field(init=False)
    date: str = field(init=False)
    time: str = field(init=False)
    date_time: str = field(init=False)
    date_time_report_str: str = field(init=False)

    def __post_init__(self) -> None:
        """Initialize."""
        self.refresh()

    def refresh(self) -> None:
        """Refresh the current date and time."""
        self._now = datetime.now(tz=UTC)
        self.date = self._now.strftime("%Y-%m-%d")
        self.time = self._now.strftime("%H-%M-%S")
        self.date_time = f"{self.date}--{self.time}"
        self.date_time_report_str = self._now.strftime("%Y-%m-%d %H:%M:%S")


_dtp = DateTimeProvider()
refresh = _dtp.refresh
date_time_report_str = _dtp.date_time_report_str
date = _dtp.date
time = _dtp.time
date_time = _dtp.date_time
