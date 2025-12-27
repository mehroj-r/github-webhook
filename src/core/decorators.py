from functools import wraps

from core import get_logger
from handlers.bot.validators.base import BaseCommandValidator

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
