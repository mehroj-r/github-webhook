"""repo message_thread_id

Revision ID: f5a1c7e9b236
Revises: e4f0a8c3d721
Create Date: 2026-10-02 02:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f5a1c7e9b236"
down_revision: Union[str, Sequence[str], None] = "e4f0a8c3d721"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("gh_repos", sa.Column("message_thread_id", sa.BigInteger(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("gh_repos", "message_thread_id")
