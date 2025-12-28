"""gh_repo.title

Revision ID: 50f03acda0d2
Revises: 86beb1e8d406
Create Date: 2025-12-28 14:33:00.175211

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "50f03acda0d2"
down_revision: Union[str, Sequence[str], None] = "86beb1e8d406"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_index(op.f("ix_gh_repos_title"), table_name="gh_repos")
    op.create_unique_constraint("repo.title_unq", "gh_repos", ["title"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("repo.title_unq", "gh_repos", type_="unique")
    op.create_index(op.f("ix_gh_repos_title"), "gh_repos", ["title"], unique=True)
