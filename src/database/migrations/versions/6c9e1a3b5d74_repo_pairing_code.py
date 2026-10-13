"""gh_repos pairing code for /connect_repo ownership checks

Revision ID: 6c9e1a3b5d74
Revises: 5b7d9f2a4c63
Create Date: 2026-10-14 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6c9e1a3b5d74"
down_revision: Union[str, Sequence[str], None] = "5b7d9f2a4c63"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("gh_repos", sa.Column("pairing_code", sa.String(length=16), nullable=True))
    op.add_column("gh_repos", sa.Column("pairing_code_expires_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("gh_repos", "pairing_code_expires_at")
    op.drop_column("gh_repos", "pairing_code")
