from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from database.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from database.models.telegram import Chat


class GithubRepository(Base, TimestampMixin):

    __tablename__ = "gh_repos"

    title: Mapped[str] = mapped_column(String(255), unique=True)
    url: Mapped[str] = mapped_column(String(500))
    chat_id: Mapped[UUID] = mapped_column(ForeignKey("tg_chats.id"))
    is_active: Mapped[bool] = mapped_column(default=True)

    chat: Mapped["Chat"] = relationship(back_populates="repositories")

    @validates("url")
    def generate_title_from_url(self, key, url):
        """Automatically generate title from URL when URL is set."""
        if url and not self.title:
            self.title = url.strip().removeprefix("https://github.com/")
        return url
