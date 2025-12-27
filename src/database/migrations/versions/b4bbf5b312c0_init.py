"""init

Revision ID: b4bbf5b312c0
Revises:
Create Date: 2025-12-27 17:33:00.111289

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b4bbf5b312c0"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "gh_repos",
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
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
    op.create_index(op.f("ix_gh_repos_chat_id"), "gh_repos", ["chat_id"], unique=False)
    op.create_index(op.f("ix_gh_repos_title"), "gh_repos", ["title"], unique=True)
    op.create_table(
        "tg_chats",
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column(
            "chat_type",
            sa.Enum("PRIVATE", "GROUP", "CHANNEL", name="chattype"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False),
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
    op.create_index(op.f("ix_tg_chats_chat_id"), "tg_chats", ["chat_id"], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_tg_chats_chat_id"), table_name="tg_chats")
    op.drop_table("tg_chats")
    op.drop_index(op.f("ix_gh_repos_title"), table_name="gh_repos")
    op.drop_index(op.f("ix_gh_repos_chat_id"), table_name="gh_repos")
    op.drop_table("gh_repos")
