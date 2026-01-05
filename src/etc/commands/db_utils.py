"""Database utility commands"""

import asyncio
import sys

from core.utils.logger import get_logger
from .base import Command, CommandRegistry
from database.models import *  # noqa: F401

logger = get_logger(__name__)


@CommandRegistry.register
class ResetDBCommand(Command):
    """Reset database (drop and recreate all tables)"""

    name = "resetdb"
    help_text = "Drop and recreate all database tables (WARNING: destructive!)"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Skip confirmation prompt",
        )

    def handle(self, yes: bool = False, **kwargs) -> None:
        """Reset the database"""
        if not yes:
            response = input("⚠️  This will DELETE ALL DATA and recreate tables. Are you sure? (yes/no): ")
            if response.lower() != "yes":
                print("❌ Operation cancelled")
                return

        print("🔄 Resetting database...")

        async def reset_database():
            from database.models.base import Base
            from database.config import engine

            async with engine.begin() as conn:
                print("Dropping existing tables...")
                await conn.run_sync(Base.metadata.drop_all)
                print("✅ Tables dropped")

                print("Creating tables...")
                await conn.run_sync(Base.metadata.create_all)
                print("✅ Tables created successfully!")

            print("✅ Database reset complete!")

        try:
            asyncio.run(reset_database())
        except Exception as e:
            print(f"❌ Error resetting database: {e}")
            sys.exit(1)
