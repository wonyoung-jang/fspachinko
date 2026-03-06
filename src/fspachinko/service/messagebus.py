"""MessageBus."""

import logging
from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ..domain.commands import Command
from ..domain.events import Event

if TYPE_CHECKING:
    from .uow import AbstractUnitOfWork

logger = logging.getLogger(__name__)

type Message = Command | Event


@dataclass(slots=True)
class MessageBus:
    """A simple message bus for handling commands and events."""

    uow: AbstractUnitOfWork
    event_handlers: dict[type[Event], list[Any]] = field(default_factory=dict)
    command_handlers: dict[type[Command], Any] = field(default_factory=dict)
    queue: deque = field(default_factory=deque)

    def handle(self, message: Message) -> None:
        """Handle a message, which can be either a command or an event."""
        self.queue.append(message)
        while self.queue:
            message = self.queue.popleft()
            if isinstance(message, Event):
                self.handle_event(message)
            elif isinstance(message, Command):
                self.handle_command(message)

    def handle_event(self, event: Event) -> None:
        """Handle an event by calling its handlers and collecting any new events that are generated."""
        for handler in self.event_handlers[type(event)]:
            try:
                logger.debug("Handling event %s with handler %s", event, handler)
                handler(event, self.uow)
                self.queue.extend(self.uow.yield_new_events())
            except Exception:
                logger.exception("Exception handling event %s", event)
                continue

    def handle_command(self, command: Command) -> None:
        """Handle a command by calling its handler and collecting any new events that are generated."""
        logger.debug("Handling command %s", command)
        try:
            handler = self.command_handlers[type(command)]
            handler(command, self.uow)
            self.queue.extend(self.uow.yield_new_events())
        except Exception:
            logger.exception("Exception handling command %s", command)
            raise
