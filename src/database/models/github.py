from typing import TYPE_CHECKING, Optional
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
    chat_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("tg_chats.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)

    chat: Mapped["Chat"] = relationship(back_populates="repositories")

    @validates("url")
    def process_url(self, key, url):
        """Validate and process the GitHub repository URL"""

        # Normalize URL by removing trailing slash
        url.rstrip("/")

        # Auto-generate title from URL if not provided
        if url and not self.title:
            self.title = url.strip().removeprefix("https://github.com/")
        return url
