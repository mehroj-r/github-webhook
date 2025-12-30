from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, String, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base, TimestampMixin
from database.enums import ChatType

if TYPE_CHECKING:
    from database.models.github import GithubRepository


class Chat(Base, TimestampMixin):

    __tablename__ = "tg_chats"

    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    title: Mapped[str | None] = mapped_column(String(255))
    chat_type: Mapped[ChatType] = mapped_column(Enum(ChatType), default=ChatType.PRIVATE)
    is_active: Mapped[bool] = mapped_column(default=True)

    repositories: Mapped[list["GithubRepository"]] = relationship(back_populates="chat")

    @classmethod
    async def get_by_repo(cls, session, repo_name: str):
        """Get the chat associated with the given repository name"""
        from sqlalchemy import select

        from database.models import GithubRepository

        return await session.scalar(
            select(cls)
            .join(cls.repositories)
            .where(GithubRepository.title == repo_name)
        )