"""MessageBus."""

import logging
from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from fspachinko.domain.commands import Command
from fspachinko.domain.events import Event

if TYPE_CHECKING:
    from collections.abc import Callable

    from .eventcollector import CompositeEventCollector


type Message = Command | Event
logger = logging.getLogger(__name__)


@dataclass(slots=True)
class MessageBus:
    """A simple message bus for handling commands and events."""

    collector: CompositeEventCollector
    event_handlers: dict[type[Event], list[Callable]]
    command_handlers: dict[type[Command], Callable]
    queue: deque = field(default_factory=deque)

    def handle(self, message: Message) -> None:
        """Handle a message, which can be either a command or an event."""
        self.queue.append(message)
        while self.queue:
            msg = self.queue.popleft()
            if isinstance(msg, Event):
                self.handle_event(msg)
            elif isinstance(msg, Command):
                self.handle_command(msg)
            else:
                error_msg = f"Message must be an Event or Command, got {type(msg)}"
                raise TypeError(error_msg)

    def handle_event(self, event: Event) -> None:
        """Handle an event by calling its handlers and collecting any new events that are generated."""
        for handler in self.event_handlers[type(event)]:
            try:
                logger.debug("Event: %s with handler %s", event, handler)
                handler(event)
                self.queue.extend(self.collector.collect_new_events())
            except Exception:
                logger.exception("Exception handling event %s", event)
                continue

    def handle_command(self, command: Command) -> None:
        """Handle a command by calling its handler and collecting any new events that are generated."""
        logger.debug("Command: %s", command)
        try:
            handler = self.command_handlers[type(command)]
            handler(command)
            self.queue.extend(self.collector.collect_new_events())
        except Exception:
            logger.exception("Exception handling command %s", command)
            raise

    def subscribe(self, message: type[Message], handler: Callable) -> None:
        """Subscribe a handler to a message type."""
        if issubclass(message, Event):
            self.event_handlers[message].append(handler)
        elif issubclass(message, Command):
            self.command_handlers[message] = handler
        else:
            msg = f"Message must be an Event or Command, got {type(message)}"
            raise TypeError(msg)
