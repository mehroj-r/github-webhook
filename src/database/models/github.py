from datetime import UTC, datetime, timedelta
from fnmatch import fnmatchcase
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import HttpUrl
from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from database.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from database.models.telegram import Chat


class GithubRepository(Base, TimestampMixin):
    __tablename__ = "gh_repos"

    title: Mapped[str] = mapped_column(String(255), unique=True)
    url: Mapped[str] = mapped_column(String(500))
    chat_id: Mapped[UUID | None] = mapped_column(ForeignKey("tg_chats.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    # NULL means "use the default event set"; otherwise the explicit list of enabled toggle keys
    enabled_events: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    # Comma-separated glob patterns; only matching branches are reported when set
    branch_filter: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Notifications are suppressed until this moment
    muted_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Forum topic (message thread) inside the chat that receives notifications
    message_thread_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    chat: Mapped["Chat | None"] = relationship(back_populates="repositories")

    @validates("url")
    def process_url(self, _, url: HttpUrl) -> str | None:
        """Validate and process the GitHub repository URL"""

        # Normalize URL by removing trailing slash
        url_str = str(url).rstrip("/")

        # Auto-generate title from URL if not provided
        if url_str and not self.title:
            self.title = url_str.strip().removeprefix("https://github.com/")
        return url_str

    @property
    def enabled_event_keys(self) -> set[str]:
        """Toggle keys currently enabled for this repository."""
        from handlers.github.catalog import DEFAULT_ENABLED_EVENTS

        if self.enabled_events is None:
            return set(DEFAULT_ENABLED_EVENTS)
        return set(self.enabled_events)

    def is_event_enabled(self, event_type: str) -> bool:
        """Whether notifications for the given GitHub event type are enabled."""
        from handlers.github.catalog import event_key

        return event_key(event_type) in self.enabled_event_keys

    def toggled_events(self, key: str) -> list[str]:
        """Return the enabled key list with `key` flipped (does not persist)."""
        from handlers.github.catalog import EVENT_KEYS

        enabled = self.enabled_event_keys
        if key in enabled:
            enabled.discard(key)
        else:
            enabled.add(key)
        return [k for k in EVENT_KEYS if k in enabled]

    @property
    def branch_patterns(self) -> list[str]:
        if not self.branch_filter:
            return []
        return [pattern.strip() for pattern in self.branch_filter.split(",") if pattern.strip()]

    def is_branch_allowed(self, branch: str | None) -> bool:
        """Whether a branch passes the filter. Events without a branch always pass."""
        patterns = self.branch_patterns
        if branch is None or not patterns:
            return True
        return any(fnmatchcase(branch, pattern) for pattern in patterns)

    @property
    def mute_remaining(self) -> timedelta | None:
        """Time left on the mute, or None when not muted."""
        if self.muted_until is None:
            return None
        until = self.muted_until if self.muted_until.tzinfo else self.muted_until.replace(tzinfo=UTC)
        remaining = until - datetime.now(UTC)
        return remaining if remaining.total_seconds() > 0 else None

    @property
    def is_muted(self) -> bool:
        return self.mute_remaining is not None
