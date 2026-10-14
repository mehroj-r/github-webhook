from datetime import UTC, datetime

from sqlalchemy import BigInteger, DateTime, String, Text, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base, TimestampMixin


class DigestItem(Base, TimestampMixin):
    """A notification held back for a repository in digest mode until the next flush."""

    __tablename__ = "tg_digest_items"

    repo_name: Mapped[str] = mapped_column(String(255), index=True)
    chat_id: Mapped[int] = mapped_column(BigInteger)
    event_type: Mapped[str] = mapped_column(String(64))
    text: Mapped[str] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    flushed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    @classmethod
    async def pending_for_repo(cls, session: AsyncSession, repo_name: str) -> list["DigestItem"]:
        stmt = select(cls).where(cls.repo_name == repo_name, cls.flushed_at.is_(None)).order_by(cls.created_at.asc())
        return list((await session.execute(stmt)).scalars().all())

    @classmethod
    async def oldest_pending(cls, session: AsyncSession, repo_name: str) -> datetime | None:
        stmt = (
            select(cls.created_at)
            .where(cls.repo_name == repo_name, cls.flushed_at.is_(None))
            .order_by(cls.created_at.asc())
            .limit(1)
        )
        return await session.scalar(stmt)

    @classmethod
    async def mark_flushed(cls, session: AsyncSession, items: list["DigestItem"]) -> None:
        if not items:
            return
        ids = [item.id for item in items]
        await session.execute(update(cls).where(cls.id.in_(ids)).values(flushed_at=datetime.now(UTC)))
