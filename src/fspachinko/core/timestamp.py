"""Provider for current date and time."""

from dataclasses import dataclass
from datetime import UTC, datetime

from .constants import DateTimeFormat


@dataclass(slots=True)
class DateTimeStamp:
    """Provider for current date and time."""

    date: str = ""
    time: str = ""
    date_time: str = ""
    date_time_report_str: str = ""

    def __post_init__(self) -> None:
        """Post-initialization tasks."""
        self.reset()

    def reset(self) -> None:
        """Refresh the current date and time."""
        now = datetime.now(tz=UTC)
        self.date = now.strftime(DateTimeFormat.DATE)
        self.time = now.strftime(DateTimeFormat.TIME)
        self.date_time = f"{self.date}--{self.time}"
        self.date_time_report_str = now.strftime(DateTimeFormat.DATETIME)
