"""repo branch_filter and muted_until

Revision ID: e4f0a8c3d721
Revises: d9e3b7a2f014
Create Date: 2026-10-02 01:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e4f0a8c3d721"
down_revision: Union[str, Sequence[str], None] = "d9e3b7a2f014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("gh_repos", sa.Column("branch_filter", sa.String(length=255), nullable=True))
    op.add_column("gh_repos", sa.Column("muted_until", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("gh_repos", "muted_until")
    op.drop_column("gh_repos", "branch_filter")
