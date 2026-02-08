"""Database utility commands"""

import asyncio
import sys

from .base import Command, CommandRegistry


@CommandRegistry.register
class CreateDBCommand(Command):
    """Create all database tables"""

    name = "createdb"
    help_text = "Create all database tables (based on models)"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--drop",
            action="store_true",
            help="Drop existing tables before creating (use with caution!)",
        )

    def handle(self, drop: bool = False, **_) -> None:
        """Create database tables"""
        print("🔄 Creating database tables...")

        async def create_tables():
            from database.config import engine

            # Import all models to register them
            from database.models import Chat, GithubRepository  # noqa: F401
            from database.models.base import Base

            async with engine.begin() as conn:
                if drop:
                    print("⚠️  Dropping existing tables...")
                    await conn.run_sync(Base.metadata.drop_all)
                    print("✅ Tables dropped")

                print("Creating tables...")
                await conn.run_sync(Base.metadata.create_all)
                print("✅ Tables created successfully!")

        try:
            asyncio.run(create_tables())
        except Exception as e:
            print(f"❌ Error creating tables: {e}")
            sys.exit(1)


@CommandRegistry.register
class DropDBCommand(Command):
    """Drop all database tables"""

    name = "dropdb"
    help_text = "Drop all database tables (WARNING: destructive!)"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Skip confirmation prompt",
        )

    def handle(self, yes: bool = False, **_) -> None:
        """Drop all database tables"""
        if not yes:
            response = input("⚠️  This will DELETE ALL TABLES. Are you sure? (yes/no): ")
            if response.lower() != "yes":
                print("❌ Operation cancelled")
                return

        print("🔄 Dropping all database tables...")

        async def drop_tables():
            from database.config import engine

            # Import all models to register them
            from database.models import Chat, GithubRepository  # noqa: F401
            from database.models.base import Base

            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
                print("✅ All tables dropped successfully!")

        try:
            asyncio.run(drop_tables())
        except Exception as e:
            print(f"❌ Error dropping tables: {e}")
            sys.exit(1)


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

    def handle(self, yes: bool = False, **_) -> None:
        """Reset the database"""
        if not yes:
            response = input("⚠️  This will DELETE ALL DATA and recreate tables. Are you sure? (yes/no): ")
            if response.lower() != "yes":
                print("❌ Operation cancelled")
                return

        print("🔄 Resetting database...")

        async def reset_database():
            from database.config import engine

            # Import all models to register them
            from database.models import Chat, GithubRepository  # noqa: F401
            from database.models.base import Base

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


@CommandRegistry.register
class ShowTablesCommand(Command):
    """Show all database tables"""

    name = "showtables"
    help_text = "Display all registered database models/tables"

    def add_arguments(self, parser) -> None:
        pass

    def handle(self, **_) -> None:
        """Show all tables"""
        print("📋 Registered database tables:")

        # Import all models to register them
        from database.models import Chat, GithubRepository  # noqa: F401
        from database.models.base import Base

        for table_name, table in Base.metadata.tables.items():
            print(f"\n  • {table_name}")
            print("    Columns:")
            for column in table.columns:
                print(f"      - {column.name}: {column.type}")
