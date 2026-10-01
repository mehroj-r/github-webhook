"""chattype supergroup

Revision ID: 3f1c2a9d7b10
Revises: 09e2ed83bb82
Create Date: 2026-10-01 23:40:00.000000

"""

from typing import Sequence, Union

from alembic import op

revision: str = "3f1c2a9d7b10"
down_revision: Union[str, Sequence[str], None] = "09e2ed83bb82"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add SUPERGROUP to the chattype enum (Telegram supergroups were rejected before)."""
    op.execute("ALTER TYPE chattype ADD VALUE IF NOT EXISTS 'SUPERGROUP'")


def downgrade() -> None:
    """PostgreSQL cannot drop a single enum value; leave the value in place."""
