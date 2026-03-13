"""Events."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Event:
    """Base class for events."""


@dataclass(slots=True, frozen=True)
class FileTransferred(Event):
    """Event after file is transferred."""

    count: int
    src: str
    dst: str


@dataclass(slots=True, frozen=True)
class DirectoryTransferred(Event):
    """Event after directory is transferred."""

    status: str
    report: str
