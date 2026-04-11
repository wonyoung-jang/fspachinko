"""MessageBus."""

import logging
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from fspachinko.domain.commands import Command
from fspachinko.domain.events import Event

if TYPE_CHECKING:
    from collections.abc import Callable

    from fspachinko.domain.model import Message


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class MessageBus:
    """A simple message bus for handling commands and events."""

    command_handlers: dict[type[Command], Callable[[Command], Any]] = field(default_factory=dict)
    event_handlers: dict[type[Event], list[Callable[[Event], None]]] = field(default_factory=dict)

    def subscribe(self, msg: type[Message], handler: Callable) -> None:
        """Subscribe a handler to a message type."""
        if issubclass(msg, Event):
            self.event_handlers[msg].append(handler)
        elif issubclass(msg, Command):
            self.command_handlers[msg] = handler

    def handle(self, msg: Message) -> None:
        """Handle a message, which can be either a command or an event."""
        if isinstance(msg, Event):
            self.handle_event(msg)
        elif isinstance(msg, Command):
            self.handle_command(msg)

    def handle_command(self, cmd: Command) -> None:
        """Handle a command by calling its handler and collecting any new events that are generated."""
        logger.debug("Command: %s", cmd)
        try:
            handler = self.command_handlers[type(cmd)]
            result = handler(cmd)
            if isinstance(result, Iterator):
                for msg in result:
                    self.handle(msg)
        except Exception:
            logger.exception("Exception handling command %s", cmd)
            raise

    def handle_event(self, evt: Event) -> None:
        """Handle an event by calling its handlers and collecting any new events that are generated."""
        for handler in self.event_handlers[type(evt)]:
            try:
                logger.debug("Event: %s with handler %s", evt, handler)
                handler(evt)
            except Exception:
                logger.exception("Exception handling event %s with handler %s", evt, handler)
                continue
