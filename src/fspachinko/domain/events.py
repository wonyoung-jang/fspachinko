"""Events."""

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class Event:
    """Base class for events."""


@dataclass(slots=True, frozen=True)
class ProcessStarted(Event):
    """Event for starting a process."""

    dir_count: int


@dataclass(slots=True, frozen=True)
class DirectoryStarted(Event):
    """Event for starting to process a directory."""

    idx: int
    target: int


@dataclass(slots=True, frozen=True)
class FileTransferred(Event):
    """Event for a file being transferred."""

    count: int


@dataclass(slots=True, frozen=True)
class ProcessStopped(Event):
    """Event for finishing the process."""


# Other


@dataclass(slots=True, frozen=True)
class FileTransferLogged(Event):
    """Event for logging a file transfer."""

    count: int
    src: str
    dst: str


@dataclass(slots=True, frozen=True)
class DirectoryLogged(Event):
    """Event for logging a directory transfer."""

    status: str
    report: str
