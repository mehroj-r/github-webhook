from sqlalchemy import BigInteger, String, UniqueConstraint
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base, TimestampMixin


class SentMessage(Base, TimestampMixin):
    """Telegram messages the bot posted for a GitHub object, so later events can edit them."""

    __tablename__ = "tg_sent_messages"
    __table_args__ = (UniqueConstraint("repo_name", "key", name="sent_message.repo_key_unq"),)

    repo_name: Mapped[str] = mapped_column(String(255), index=True)
    # e.g. "workflow_run:123456:1" (object kind, id, attempt)
    key: Mapped[str] = mapped_column(String(128))
    chat_id: Mapped[int] = mapped_column(BigInteger)
    message_id: Mapped[int] = mapped_column(BigInteger)

    @classmethod
    async def find(cls, session: AsyncSession, repo_name: str, key: str) -> "SentMessage | None":
        return await cls.get(session, repo_name=repo_name, key=key)

    @classmethod
    async def remember(
        cls, session: AsyncSession, repo_name: str, key: str, chat_id: int, message_id: int
    ) -> "SentMessage":
        return await cls.create_or_update(
            session, defaults={"chat_id": chat_id, "message_id": message_id}, repo_name=repo_name, key=key
        )
