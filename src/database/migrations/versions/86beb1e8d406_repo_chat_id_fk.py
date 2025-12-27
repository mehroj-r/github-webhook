"""repo.chat_id fk

Revision ID: 86beb1e8d406
Revises: b4bbf5b312c0
Create Date: 2025-12-28 00:15:35.656601

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pygments.lexer import using

revision: str = "86beb1e8d406"
down_revision: Union[str, Sequence[str], None] = "b4bbf5b312c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade() -> None:
    # 1. Add temp UUID column
    op.add_column(
        "gh_repos",
        sa.Column("chat_id_uuid", postgresql.UUID(), nullable=True),
    )

    # 2. Populate it
    op.execute(
        """
        UPDATE gh_repos
        SET chat_id_uuid = tg_chats.id
        FROM tg_chats
        WHERE tg_chats.chat_id = gh_repos.chat_id
        """
    )

    # 3. Drop FK / index
    op.drop_index(op.f("ix_gh_repos_chat_id"), table_name="gh_repos")

    # 4. Drop old column
    op.drop_column("gh_repos", "chat_id")

    # 5. Rename temp column
    op.alter_column(
        "gh_repos",
        "chat_id_uuid",
        new_column_name="chat_id",
        nullable=False,
    )

    # 6. Recreate FK
    op.create_foreign_key(
        "repo.chat_id.fk.chat.id",
        "gh_repos",
        "tg_chats",
        ["chat_id"],
        ["id"],
    )


def downgrade() -> None:
    # 1. Drop FK
    op.drop_constraint(
        "repo.chat_id.fk.chat.id",
        "gh_repos",
        type_="foreignkey",
    )

    # 2. Add temp BIGINT column
    op.add_column(
        "gh_repos",
        sa.Column("chat_id_bigint", sa.BIGINT(), nullable=True),
    )

    # 3. Populate using JOIN
    op.execute(
        """
        UPDATE gh_repos
        SET chat_id_bigint = tg_chats.chat_id
        FROM tg_chats
        WHERE tg_chats.id = gh_repos.chat_id
        """
    )

    # 4. Drop UUID column
    op.drop_column("gh_repos", "chat_id")

    # 5. Rename back
    op.alter_column(
        "gh_repos",
        "chat_id_bigint",
        new_column_name="chat_id",
        nullable=True,
    )

    # 6. Restore index
    op.create_index(
        op.f("ix_gh_repos_chat_id"),
        "gh_repos",
        ["chat_id"],
        unique=False,
    )
