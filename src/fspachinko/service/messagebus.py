"""MessageBus."""

import logging
from collections.abc import Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING

from fspachinko.domain.commands import Command
from fspachinko.domain.events import Event

if TYPE_CHECKING:
    from collections.abc import Callable

    from fspachinko.domain.model import Message


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class MessageBus:
    """A simple message bus for handling commands and events."""

    command_handlers: dict[type[Command], Callable]
    event_handlers: dict[type[Event], list[Callable]]

    def subscribe(self, message: type[Message], handler: Callable) -> None:
        """Subscribe a handler to a message type."""
        if issubclass(message, Event):
            self.event_handlers[message].append(handler)
        elif issubclass(message, Command):
            self.command_handlers[message] = handler

    def handle(self, message: Message) -> None:
        """Handle a message, which can be either a command or an event."""
        if isinstance(message, Event):
            self.handle_event(message)
        elif isinstance(message, Command):
            self.handle_command(message)

    def handle_command(self, command: Command) -> None:
        """Handle a command by calling its handler and collecting any new events that are generated."""
        logger.debug("Command: %s", command)
        try:
            handler = self.command_handlers[type(command)]
            result = handler(command)
            if isinstance(result, Iterator):
                for msg in result:
                    self.handle(msg)
        except Exception:
            logger.exception("Exception handling command %s", command)
            raise

    def handle_event(self, event: Event) -> None:
        """Handle an event by calling its handlers and collecting any new events that are generated."""
        for handler in self.event_handlers[type(event)]:
            try:
                logger.debug("Event: %s with handler %s", event, handler)
                handler(event)
            except Exception:
                logger.exception("Exception handling event %s", event)
                continue
