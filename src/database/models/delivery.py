from datetime import UTC, datetime

from sqlalchemy import DateTime, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from database.enums import DeliveryStatus
from database.models.base import Base, TimestampMixin


class WebhookDelivery(Base, TimestampMixin):
    """One row per GitHub webhook delivery, used for idempotency and debugging."""

    __tablename__ = "gh_deliveries"

    delivery_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    hook_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    action: Mapped[str | None] = mapped_column(String(64), nullable=True)
    repo_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(16), default=DeliveryStatus.RECEIVED.value)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @classmethod
    async def start(
        cls,
        session: AsyncSession,
        *,
        delivery_id: str,
        event_type: str,
        hook_id: str | None = None,
    ) -> tuple["WebhookDelivery", bool]:
        """Record an incoming delivery. Returns (row, is_new); is_new is False for redeliveries."""
        existing = await cls.get(session, delivery_id=delivery_id)
        if existing:
            return existing, False

        row = await cls.create(session, delivery_id=delivery_id, event_type=event_type, hook_id=hook_id)
        return row, True

    async def finish(
        self,
        session: AsyncSession,
        status: DeliveryStatus,
        *,
        error: str | None = None,
        action: str | None = None,
        repo_name: str | None = None,
    ) -> None:
        """Mark the delivery as finished with the given status."""
        await self.update(
            session,
            status=status.value,
            error=(error or None) and error[:2000],
            action=action if action is not None else self.action,
            repo_name=repo_name if repo_name is not None else self.repo_name,
            processed_at=datetime.now(UTC),
        )

    @property
    def is_processed(self) -> bool:
        return self.status == DeliveryStatus.PROCESSED.value

    @classmethod
    async def latest_for_repos(
        cls, session: AsyncSession, repo_names: list[str], limit: int = 10
    ) -> list["WebhookDelivery"]:
        """Return the most recent deliveries for the given repository names."""
        if not repo_names:
            return []
        stmt = select(cls).where(cls.repo_name.in_(repo_names)).order_by(cls.created_at.desc()).limit(limit)
        return list((await session.execute(stmt)).scalars().all())
