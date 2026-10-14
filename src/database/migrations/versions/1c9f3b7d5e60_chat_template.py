"""chat template

Revision ID: 1c9f3b7d5e60
Revises: 0b6d9e4a1c87
Create Date: 2026-10-02 03:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "1c9f3b7d5e60"
down_revision: Union[str, Sequence[str], None] = "0b6d9e4a1c87"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "tg_chats",
        sa.Column("template", sa.String(length=16), nullable=False, server_default="verbose"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("tg_chats", "template")
