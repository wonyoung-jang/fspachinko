"""Model classes for the domain."""

from dataclasses import dataclass, field


@dataclass(slots=True, frozen=True)
class Event:
    """Base class for events."""


@dataclass(slots=True, frozen=True)
class ProcessFinishedEvent(Event):
    """Event representing the completion of a process."""

    status: str
    msg: str


@dataclass(slots=True, frozen=True)
class FSEntry:
    """Value object wrapper for os.DirEntry."""

    path: str
    stem: str
    ext: str
    parent: str
    size: int


@dataclass(slots=True)
class FSPachinkoPin:
    """Represents a 'pin' on the Pachinko board."""

    path: str
    is_scanned: bool = False
    subdirs: list[str] = field(default_factory=list)
    files: list[FSEntry] = field(default_factory=list)
