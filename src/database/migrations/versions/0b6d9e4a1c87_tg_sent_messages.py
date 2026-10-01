"""tg_sent_messages

Revision ID: 0b6d9e4a1c87
Revises: f5a1c7e9b236
Create Date: 2026-10-02 03:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0b6d9e4a1c87"
down_revision: Union[str, Sequence[str], None] = "f5a1c7e9b236"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "tg_sent_messages",
        sa.Column("repo_name", sa.String(length=255), nullable=False),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("message_id", sa.BigInteger(), nullable=False),
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
        sa.UniqueConstraint("repo_name", "key", name="sent_message.repo_key_unq"),
    )
    op.create_index(op.f("ix_tg_sent_messages_repo_name"), "tg_sent_messages", ["repo_name"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_tg_sent_messages_repo_name"), table_name="tg_sent_messages")
    op.drop_table("tg_sent_messages")
