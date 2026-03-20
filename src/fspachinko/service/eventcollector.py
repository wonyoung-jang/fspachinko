"""Event collector aggregate handler."""

from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Iterator

    from fspachinko.domain.events import Event


class EventEmitterProtocol(Protocol):
    """Protocol for event emitters."""

    def collect_new_events(self) -> Iterator[Event]:
        """Collect new events that were generated during the transaction."""


@dataclass(slots=True)
class CompositeEventCollector:
    """Aggregate handler for collecting events."""

    event_emitters: list[EventEmitterProtocol] = field(default_factory=list)
    events: deque = field(default_factory=deque)

    def collect_new_events(self) -> Iterator[Event]:
        """Collect new events from all event emitters."""
        for emitter in self.event_emitters:
            self.events.extend(emitter.collect_new_events())
            while self.events:
                yield self.events.popleft()

    def register_emitter(self, emitter: EventEmitterProtocol) -> None:
        """Register an event emitter."""
        self.event_emitters.append(emitter)
