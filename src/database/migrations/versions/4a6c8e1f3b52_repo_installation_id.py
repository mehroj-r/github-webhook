"""gh_repos.installation_id for GitHub App installations

Revision ID: 4a6c8e1f3b52
Revises: 2d7e5f8a9b41
Create Date: 2026-10-14 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4a6c8e1f3b52"
down_revision: Union[str, Sequence[str], None] = "2d7e5f8a9b41"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("gh_repos", sa.Column("installation_id", sa.BigInteger(), nullable=True))
    op.create_index(op.f("ix_gh_repos_installation_id"), "gh_repos", ["installation_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_gh_repos_installation_id"), table_name="gh_repos")
    op.drop_column("gh_repos", "installation_id")
