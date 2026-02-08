from collections.abc import Awaitable
from typing import Protocol

from handlers.github.models.events import BaseEvent


class EventHandler(Protocol):
    def __call__(self, *, event: BaseEvent) -> Awaitable[None]: ...
