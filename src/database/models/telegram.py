from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.enums import ChatType, MessageTemplate
from database.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from database.models.github import GithubRepository


class Chat(Base, TimestampMixin):
    __tablename__ = "tg_chats"

    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    title: Mapped[str | None] = mapped_column(String(255))
    chat_type: Mapped[ChatType] = mapped_column(Enum(ChatType), default=ChatType.PRIVATE)
    is_active: Mapped[bool] = mapped_column(default=True)
    managed_by_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    # Message style for notifications: verbose (bodies, lists) or compact (headline lines only)
    template: Mapped[str] = mapped_column(String(16), default=MessageTemplate.VERBOSE.value, server_default="verbose")

    repositories: Mapped[list["GithubRepository"]] = relationship(back_populates="chat")

    @property
    def is_compact(self) -> bool:
        return self.template == MessageTemplate.COMPACT.value
