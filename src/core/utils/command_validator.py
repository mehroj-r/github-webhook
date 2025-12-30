from abc import ABC
from typing import final

from core import get_logger

logger = get_logger(__name__)


class BaseCommandValidator(ABC):
    """Base class for command validators."""

    arguments: list[str] = []  # List of argument names to validate
    error_msg: str = "An error has occurred"  # Default error message

    async def validate__length(self, args_data: dict) -> tuple[bool, str]:
        """Validate the number of arguments."""
        if len(self.arguments) != len(args_data):
            return False, self.error_msg

        return True, ""

    async def validate(self, args_data: dict) -> tuple[bool, str]:
        """Validate arguments by dynamically calling validate_{arg_name} methods."""

        # First, validate the length of arguments
        await self.validate__length(args_data=args_data)

        # Then, validate each argument
        for arg, value in args_data.items():

            # Check if argument is valid
            if arg not in self.arguments:
                logger.error(f"Argument {arg} is not valid.")
                return False, self.error_msg

            # Dynamically call the validation method for the argument
            is_valid, error_msg = await self._validate(arg, value)

            # If validation fails, return the error message
            if not is_valid:
                return False, error_msg

        return True, ""

    @final
    async def _validate(self, arg: str, value: str) -> tuple[bool, str]:
        method_name = f"validate_{arg}"
        if hasattr(self, method_name):
            method = getattr(self, method_name)
            return await method(value)

        raise AttributeError(f"Validator method {method_name} not found.")
