"""MessageBus."""

import logging
from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ..domain.commands import Command
from ..domain.events import Event

if TYPE_CHECKING:
    from .handlers import Message
    from .uow import AbstractUnitOfWork

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class MessageBus:
    """A simple message bus for handling commands and events."""

    uow: AbstractUnitOfWork
    event_handlers: dict[type[Event], list[Any]] = field(default_factory=dict)
    command_handlers: dict[type[Command], Any] = field(default_factory=dict)
    queue: deque = field(default_factory=deque)

    def handle(self, message: Message, **kwargs: object) -> None:
        """Handle a message, which can be either a command or an event."""
        self.queue.append(message)
        while self.queue:
            msg = self.queue.popleft()
            if isinstance(msg, Event):
                self.handle_event(msg, **kwargs)
            elif isinstance(msg, Command):
                self.handle_command(msg, **kwargs)
            else:
                msg = f"Message must be an Event or Command, got {type(msg)}"
                logger.error(msg)
                raise TypeError(msg)

    def handle_event(self, event: Event, **kwargs: object) -> None:
        """Handle an event by calling its handlers and collecting any new events that are generated."""
        for handler in self.event_handlers[type(event)]:
            try:
                logger.debug("Event: %s with handler %s", event, handler)
                handler(event, **kwargs)
            except Exception:
                logger.exception("Exception handling event %s", event)
                continue

    def handle_command(self, command: Command, **kwargs: object) -> None:
        """Handle a command by calling its handler and collecting any new events that are generated."""
        logger.debug("Command: %s", command)
        try:
            handler = self.command_handlers[type(command)]
            handler(command, **kwargs)
        except Exception:
            logger.exception("Exception handling command %s", command)
            raise
