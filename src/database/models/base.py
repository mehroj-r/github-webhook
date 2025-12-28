import uuid

from datetime import datetime, UTC
from uuid import UUID

from sqlalchemy import DateTime, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase

from .orm.manager import BaseORMClass


class Base(BaseORMClass, DeclarativeBase):
    """Base class for all database models."""

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    async def update(self, session: AsyncSession, **kwargs) -> None:
        """Update the model instance with given keyword arguments."""
        for key, value in kwargs.items():
            setattr(self, key, value)
        session.add(self)
        await session.flush()

    async def delete(self, session: AsyncSession) -> None:
        """Delete the model instance from the database."""
        await session.delete(self)
        await session.flush()

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
