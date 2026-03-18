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

    path: str
    size: int
    count: int
    target_qty: int
    is_success: bool
    is_empty_creation: bool
    is_stop_requested: bool
    is_root_locked: bool
