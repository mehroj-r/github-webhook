"""digest items and interval

Revision ID: 2d7e5f8a9b41
Revises: 1c9f3b7d5e60
Create Date: 2026-10-02 04:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2d7e5f8a9b41"
down_revision: Union[str, Sequence[str], None] = "1c9f3b7d5e60"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("gh_repos", sa.Column("digest_interval_minutes", sa.Integer(), nullable=True))
    op.create_table(
        "tg_digest_items",
        sa.Column("repo_name", sa.String(length=255), nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=True),
        sa.Column("flushed_at", sa.DateTime(timezone=True), nullable=True),
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
    op.create_index(op.f("ix_tg_digest_items_repo_name"), "tg_digest_items", ["repo_name"], unique=False)
    op.create_index(op.f("ix_tg_digest_items_flushed_at"), "tg_digest_items", ["flushed_at"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_tg_digest_items_flushed_at"), table_name="tg_digest_items")
    op.drop_index(op.f("ix_tg_digest_items_repo_name"), table_name="tg_digest_items")
    op.drop_table("tg_digest_items")
    op.drop_column("gh_repos", "digest_interval_minutes")
