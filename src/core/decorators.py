from functools import wraps
from typing import Callable, TYPE_CHECKING
import inspect

from core import get_logger
from core.enums import GHEventType
from database import async_session_maker
from core.utils.command_validator import BaseCommandValidator

if TYPE_CHECKING:
    from handlers.github.models.events import BaseEvent

logger = get_logger(__name__)


def parse_command(arguments: list, validator: BaseCommandValidator):
    """Decorator to parse command arguments from message text"""

    def decorator(handler):

        @wraps(handler)
        async def wrapper(message, *args, **kwargs):

            # Initialize parsed arguments
            parsed_arguments = {}
            for argument in arguments:
                parsed_arguments[argument] = ""

            try:
                parts = message.text.strip().split(" ")

                # Extract command arguments
                command_args = parts[1:] if len(parts) > 1 else []

                # Parse arguments
                if len(command_args) == len(arguments):
                    for i, argument in enumerate(arguments):
                        parsed_arguments[argument] = command_args[i]

                # Validate arguments if validator is provided
                is_valid, error_msg = await validator.validate(args_data=parsed_arguments)
                if not is_valid:
                    raise Exception(error_msg)

                # Pass parsed arguments to the handler
                kwargs.update(parsed_arguments)

            except Exception as e:
                logger.error("Error parsing command: %s", e)
                await message.reply(str(e))
                return None

            return await handler(message, *args, **kwargs)

        return wrapper

    return decorator


class GitHubEventRegistry:
    """Registry for GitHub event handlers"""

    _registry = {}

    @classmethod
    def _extract_event_model(cls, handler: Callable) -> type["BaseEvent"]:
        sig = inspect.signature(handler)
        params = sig.parameters

        if "event" not in params:
            raise ValueError(f"Handler {handler.__name__} must have an 'event' parameter")

        event_param = params["event"]
        if event_param.annotation == inspect.Parameter.empty:
            raise ValueError(f"Handler {handler.__name__} must have a type hint for 'event' parameter")

        return event_param.annotation

    @classmethod
    def register(cls, event: GHEventType) -> Callable:

        def decorator(handler) -> Callable:

            model = cls._extract_event_model(handler)

            @wraps(handler)
            async def wrapper(*args, **kwargs) -> None:

                # Create a new database session for each event handling
                async with async_session_maker() as session:
                    kwargs["session"] = session
                    try:
                        result = await handler(*args, **kwargs)
                        await session.commit()
                        return result
                    except Exception as e:
                        logger.error("Error handling GitHub event: %s", e)
                        await session.rollback()
                        raise
            
            cls._registry[event] = {
                "handler": wrapper,
                "model": model,
            }

            return wrapper

        return decorator

    @classmethod
    def get_handler(cls, event: GHEventType) -> Callable:
        return cls._registry.get(event, {}).get("handler")

    @classmethod
    def get_event_model(cls, event: GHEventType) -> "BaseEvent":
        return cls._registry.get(event, {}).get("model")
