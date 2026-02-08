from abc import ABC, abstractmethod


class Command(ABC):
    """Base class for all management commands"""

    name: str = ""
    help_text: str = ""

    @abstractmethod
    def add_arguments(self, parser) -> None:
        """Add command-specific arguments to the parser"""
        pass

    @abstractmethod
    def handle(self, **kwargs) -> None:
        """Execute the command"""
        pass


class CommandRegistry:
    """Registry for all available commands"""

    _commands: dict[str, type[Command]] = {}

    @classmethod
    def register(cls, command_class: type[Command]) -> type[Command]:
        """Register a command"""
        if not command_class.name:
            raise ValueError(f"Command {command_class.__name__} must have a name")
        cls._commands[command_class.name] = command_class
        return command_class

    @classmethod
    def get_command(cls, name: str) -> type[Command]:
        """Get a command by name"""
        if name not in cls._commands:
            raise ValueError(f"Command '{name}' not found")
        return cls._commands[name]

    @classmethod
    def get_all_commands(cls) -> dict[str, type[Command]]:
        """Get all registered commands"""
        return cls._commands.copy()

    @classmethod
    def list_commands(cls) -> list[str]:
        """List all command names"""
        return list(cls._commands.keys())
