from typing import Protocol, Awaitable

from handlers.github.models.events import BaseEvent


class EventHandler(Protocol):
    def __call__(self, *, event: BaseEvent) -> Awaitable[None]: ...
