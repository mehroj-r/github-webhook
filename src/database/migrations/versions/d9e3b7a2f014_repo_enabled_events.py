"""repo enabled_events

Revision ID: d9e3b7a2f014
Revises: c2b8f61e4d55
Create Date: 2026-10-02 01:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d9e3b7a2f014"
down_revision: Union[str, Sequence[str], None] = "c2b8f61e4d55"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("gh_repos", sa.Column("enabled_events", sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("gh_repos", "enabled_events")
