"""chat managed_by_user_id

Revision ID: c2b8f61e4d55
Revises: a7d4e2c91b03
Create Date: 2026-10-02 00:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c2b8f61e4d55"
down_revision: Union[str, Sequence[str], None] = "a7d4e2c91b03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("tg_chats", sa.Column("managed_by_user_id", sa.BigInteger(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("tg_chats", "managed_by_user_id")
