"""Server and application commands"""

import asyncio
import sys

from .base import Command, CommandRegistry


@CommandRegistry.register
class RunServerCommand(Command):
    """Run the application server"""

    name = "runserver"
    help_text = "Start the application (bot and/or webhook server)"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--host",
            type=str,
            help="Server host (overrides config)",
        )
        parser.add_argument(
            "--port",
            type=int,
            help="Server port (overrides config)",
        )
        parser.add_argument(
            "--reload",
            action="store_true",
            help="Enable auto-reload on code changes",
        )

    def handle(self, host: str = None, port: int = None, reload: bool = False, **kwargs) -> None:
        """Run the server"""
        from main import main as run_main

        print("🚀 Starting application...")

        # Override settings if provided
        if host or port:
            from config import settings as config_settings

            if host:
                config_settings.HOST = host
            if port:
                config_settings.PORT = port

        if reload:
            print("⚠️  Auto-reload mode requires manual setup with uvicorn")
            print("Run: uvicorn main:app --reload")
            return

        try:
            asyncio.run(run_main())
        except KeyboardInterrupt:
            print("\n👋 Shutting down...")
        except Exception as e:
            print(f"❌ Error running server: {e}")
            sys.exit(1)


@CommandRegistry.register
class ShellCommand(Command):
    """Start an interactive Python shell with app context"""

    name = "shell"
    help_text = "Start an interactive Python shell with application context"

    def add_arguments(self, parser) -> None:
        pass

    def handle(self, **kwargs) -> None:
        """Start interactive shell"""
        import code

        # Import commonly used modules
        from config import settings
        from database.config import engine, async_session_maker
        from database import models

        banner = """
🐍 Python Shell - Application Context Loaded

Available objects:
  - settings: Application settings
  - engine: SQLAlchemy async engine
  - async_session_maker: Database session factory
  - models: Database models

Example usage:
  async with async_session_maker() as session:
      result = await session.execute(select(Chat))
      chats = result.scalars().all()
"""

        local_vars = {
            "settings": settings,
            "engine": engine,
            "async_session_maker": async_session_maker,
            "models": models,
        }

        code.interact(banner=banner, local=local_vars)
