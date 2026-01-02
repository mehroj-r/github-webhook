"""nullable_chat_id

Revision ID: 09e2ed83bb82
Revises: 50f03acda0d2
Create Date: 2026-01-02 23:52:44.315465

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "09e2ed83bb82"
down_revision: Union[str, Sequence[str], None] = "50f03acda0d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column("gh_repos", "chat_id", existing_type=sa.UUID(), nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column("gh_repos", "chat_id", existing_type=sa.UUID(), nullable=False)
