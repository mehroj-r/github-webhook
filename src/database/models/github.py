from uuid import UUID

from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base, TimestampMixin


class GithubRepository(Base, TimestampMixin):

    __tablename__ = "gh_repos"

    title: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    url: Mapped[str] = mapped_column(String(500))
    chat_id: Mapped[UUID] = mapped_column(ForeignKey("tg_chats.id"))
    is_active: Mapped[bool] = mapped_column(default=True)
