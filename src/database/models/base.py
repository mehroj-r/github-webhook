import uuid

from datetime import datetime, UTC
from uuid import UUID

from sqlalchemy import DateTime, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all database models."""

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    @classmethod
    async def get_or_create(cls, session: AsyncSession, defaults: dict | None = None, **kwargs):
        """Get an existing record or create a new one."""
        from sqlalchemy import select

        stmt = select(cls).filter_by(**kwargs)
        result = await session.execute(stmt)
        instance = result.scalars().first()
        if instance:
            return instance, False
        else:
            params = {**kwargs}
            if defaults:
                params.update(defaults)
            instance = cls(**params)
            session.add(instance)
            await session.flush()
            return instance, True

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id})>"


class TimestampMixin:
    """Mixin to add created_at and updated_at timestamp columns."""

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class SoftDeleteMixin:
    """Mixin to add soft delete functionality."""

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def delete(self):
        """Mark the record as deleted by setting deleted_at timestamp."""
        # TODO: Consider removing related records in other tables
        self.deleted_at = datetime.now(UTC)
