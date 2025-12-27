"""Database migration commands using Alembic"""

import subprocess
import sys
from pathlib import Path

from .base import Command, CommandRegistry


@CommandRegistry.register
class MakeMigrationsCommand(Command):
    """Create a new migration file"""

    name = "makemigrations"
    help_text = "Generate a new Alembic migration based on model changes"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "-m",
            "--message",
            type=str,
            help="Migration message/description",
            required=False,
        )
        parser.add_argument(
            "--autogenerate",
            action="store_true",
            default=True,
            help="Automatically detect changes (default: True)",
        )

    def handle(self, message: str = None, autogenerate: bool = True, **kwargs) -> None:
        """Generate a new migration"""
        print("🔄 Generating migration...")

        # Get the database directory path
        db_dir = Path(__file__).resolve().parents[2] / "database"
        alembic_ini = db_dir / "alembic.ini"

        if not alembic_ini.exists():
            print(f"❌ Error: alembic.ini not found at {alembic_ini}")
            sys.exit(1)

        # Build the alembic command
        cmd = ["alembic", "-c", str(alembic_ini), "revision"]

        if autogenerate:
            cmd.append("--autogenerate")

        if message:
            cmd.extend(["-m", message])
        else:
            cmd.extend(["-m", "auto_migration"])

        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(result.stdout)
            if result.stderr:
                print(result.stderr)
            print("✅ Migration generated successfully!")
        except subprocess.CalledProcessError as e:
            print(f"❌ Error generating migration: {e}")
            if e.stdout:
                print(e.stdout)
            if e.stderr:
                print(e.stderr)
            sys.exit(1)


@CommandRegistry.register
class MigrateCommand(Command):
    """Apply database migrations"""

    name = "migrate"
    help_text = "Apply pending migrations to the database"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "revision",
            type=str,
            nargs="?",
            default="head",
            help="Target revision (default: head)",
        )

    def handle(self, revision: str = "head", **kwargs) -> None:
        """Apply migrations"""
        print(f"🔄 Applying migrations to {revision}...")

        db_dir = Path(__file__).resolve().parents[2] / "database"
        alembic_ini = db_dir / "alembic.ini"

        if not alembic_ini.exists():
            print(f"❌ Error: alembic.ini not found at {alembic_ini}")
            sys.exit(1)

        cmd = ["alembic", "-c", str(alembic_ini), "upgrade", revision]

        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(result.stdout)
            if result.stderr:
                print(result.stderr)
            print("✅ Migrations applied successfully!")
        except subprocess.CalledProcessError as e:
            print(f"❌ Error applying migrations: {e}")
            if e.stdout:
                print(e.stdout)
            if e.stderr:
                print(e.stderr)
            sys.exit(1)


@CommandRegistry.register
class DowngradeCommand(Command):
    """Downgrade database to a previous migration"""

    name = "downgrade"
    help_text = "Rollback migrations to a specific revision"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "revision",
            type=str,
            nargs="?",
            default="-1",
            help="Target revision (default: -1 for one step back)",
        )

    def handle(self, revision: str = "-1", **kwargs) -> None:
        """Downgrade migrations"""
        print(f"🔄 Downgrading to {revision}...")

        db_dir = Path(__file__).resolve().parents[2] / "database"
        alembic_ini = db_dir / "alembic.ini"

        if not alembic_ini.exists():
            print(f"❌ Error: alembic.ini not found at {alembic_ini}")
            sys.exit(1)

        cmd = ["alembic", "-c", str(alembic_ini), "downgrade", revision]

        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(result.stdout)
            if result.stderr:
                print(result.stderr)
            print("✅ Downgrade completed successfully!")
        except subprocess.CalledProcessError as e:
            print(f"❌ Error during downgrade: {e}")
            if e.stdout:
                print(e.stdout)
            if e.stderr:
                print(e.stderr)
            sys.exit(1)


@CommandRegistry.register
class CurrentCommand(Command):
    """Show current migration revision"""

    name = "current"
    help_text = "Display the current migration revision"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "-v",
            "--verbose",
            action="store_true",
            help="Show verbose output",
        )

    def handle(self, verbose: bool = False, **kwargs) -> None:
        """Show current revision"""
        print("🔍 Checking current migration revision...")

        db_dir = Path(__file__).resolve().parents[2] / "database"
        alembic_ini = db_dir / "alembic.ini"

        if not alembic_ini.exists():
            print(f"❌ Error: alembic.ini not found at {alembic_ini}")
            sys.exit(1)

        cmd = ["alembic", "-c", str(alembic_ini), "current"]
        if verbose:
            cmd.append("-v")

        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(result.stdout)
            if result.stderr:
                print(result.stderr)
        except subprocess.CalledProcessError as e:
            print(f"❌ Error: {e}")
            if e.stdout:
                print(e.stdout)
            if e.stderr:
                print(e.stderr)
            sys.exit(1)


@CommandRegistry.register
class HistoryCommand(Command):
    """Show migration history"""

    name = "history"
    help_text = "Display migration history"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "-r",
            "--range",
            type=str,
            help="Range of revisions to show (e.g., base:head)",
        )

    def handle(self, range: str = None, **kwargs) -> None:
        """Show migration history"""
        print("📜 Migration history:")

        db_dir = Path(__file__).resolve().parents[2] / "database"
        alembic_ini = db_dir / "alembic.ini"

        if not alembic_ini.exists():
            print(f"❌ Error: alembic.ini not found at {alembic_ini}")
            sys.exit(1)

        cmd = ["alembic", "-c", str(alembic_ini), "history"]
        if range:
            cmd.extend(["-r", range])

        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(result.stdout)
            if result.stderr:
                print(result.stderr)
        except subprocess.CalledProcessError as e:
            print(f"❌ Error: {e}")
            if e.stdout:
                print(e.stdout)
            if e.stderr:
                print(e.stderr)
            sys.exit(1)
