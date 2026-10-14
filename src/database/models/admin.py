from sqlalchemy import BigInteger, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base, TimestampMixin


class BotAdmin(Base, TimestampMixin):
    """Telegram users with bot-wide admin rights, managed at runtime by the owner (MASTER_CHAT_ID)."""

    __tablename__ = "bot_admins"

    user_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    # Display name captured when the admin was added, for /admins
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    added_by_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    @classmethod
    async def is_admin(cls, session: AsyncSession, user_id: int) -> bool:
        return await session.scalar(select(cls.id).where(cls.user_id == user_id)) is not None

    @classmethod
    async def all(cls, session: AsyncSession) -> list["BotAdmin"]:
        return list((await session.scalars(select(cls).order_by(cls.created_at))).all())
