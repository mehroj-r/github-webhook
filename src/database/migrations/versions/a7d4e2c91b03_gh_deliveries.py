"""gh_deliveries

Revision ID: a7d4e2c91b03
Revises: 3f1c2a9d7b10
Create Date: 2026-10-02 00:10:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a7d4e2c91b03"
down_revision: Union[str, Sequence[str], None] = "3f1c2a9d7b10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "gh_deliveries",
        sa.Column("delivery_id", sa.String(length=64), nullable=False),
        sa.Column("hook_id", sa.String(length=64), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=True),
        sa.Column("repo_name", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_gh_deliveries_delivery_id"), "gh_deliveries", ["delivery_id"], unique=True)
    op.create_index(op.f("ix_gh_deliveries_event_type"), "gh_deliveries", ["event_type"], unique=False)
    op.create_index(op.f("ix_gh_deliveries_repo_name"), "gh_deliveries", ["repo_name"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_gh_deliveries_repo_name"), table_name="gh_deliveries")
    op.drop_index(op.f("ix_gh_deliveries_event_type"), table_name="gh_deliveries")
    op.drop_index(op.f("ix_gh_deliveries_delivery_id"), table_name="gh_deliveries")
    op.drop_table("gh_deliveries")
