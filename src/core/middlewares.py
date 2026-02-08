from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from database import async_session_maker


class DatabaseMiddleware(BaseMiddleware):
    """
    Middleware that injects database session into handler context.
    The session is automatically committed on success or rolled back on error.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """
        Inject database session into handler data.

        Args:
            handler: The handler function
            event: The telegram event (Message, CallbackQuery, etc.)
            data: The data dictionary that will be passed to the handler

        Returns:
            The result of the handler
        """
        async with async_session_maker() as session:
            data["session"] = session
            try:
                result = await handler(event, data)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise
