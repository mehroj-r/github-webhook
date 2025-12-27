#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

# Add the src directory to the path
src_path = Path(__file__).parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from etc.commands import CommandRegistry


def main():
    """Main entry point for the management script"""

    # Create the main parser
    parser = argparse.ArgumentParser(
        description="Management script for GitHub Webhook application",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Create subparsers for each command
    subparsers = parser.add_subparsers(
        dest="command",
        help="Available commands",
        required=True,
    )

    # Register all commands
    command_instances = {}
    for command_name, command_class in CommandRegistry.get_all_commands().items():
        # Create subparser for this command
        command_parser = subparsers.add_parser(
            command_name,
            help=command_class.help_text,
        )

        # Instantiate the command and let it add its arguments
        command_instance = command_class()
        command_instance.add_arguments(command_parser)
        command_instances[command_name] = command_instance

    # Parse arguments
    args = parser.parse_args()

    # Get the command and execute it
    command = command_instances[args.command]

    # Convert args to dict and remove the command name
    kwargs = vars(args)
    kwargs.pop("command")

    # Execute the command
    try:
        command.handle(**kwargs)
    except KeyboardInterrupt:
        print("\n👋 Operation cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        if "--debug" in sys.argv or "-d" in sys.argv:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
