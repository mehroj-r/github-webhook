from typing import Optional, Self

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase


class BaseORMClass(DeclarativeBase):
    """Base class for ORM models."""

    @classmethod
    async def get(cls, session: AsyncSession, **kwargs) -> Optional[Self]:
        """Get a single record matching the given criteria."""
        from sqlalchemy import select

        stmt = select(cls).filter_by(**kwargs)
        result = await session.execute(stmt)
        return result.scalars().first()

    @classmethod
    async def filter(cls, session: AsyncSession, **kwargs) -> list[Self]:
        """Get all records matching the given criteria."""
        from sqlalchemy import select

        stmt = select(cls).filter_by(**kwargs)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @classmethod
    async def create(cls, session: AsyncSession, **kwargs) -> Self:
        """Create a new record with the given attributes."""
        instance = cls(**kwargs)
        session.add(instance)
        await session.flush()
        return instance

    @classmethod
    async def get_or_create(cls, session: AsyncSession, defaults: Optional[dict] = None, **kwargs) -> tuple[Self, bool]:
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

    @classmethod
    async def create_or_update(cls, session: AsyncSession, defaults: Optional[dict] = None, **kwargs) -> Self:
        """Create a new record or update an existing one."""
        from sqlalchemy import select

        stmt = select(cls).filter_by(**kwargs)
        result = await session.execute(stmt)
        instance = result.scalars().first()
        if instance:
            if defaults:
                for key, value in defaults.items():
                    setattr(instance, key, value)
            await session.flush()
            return instance
        else:
            params = {**kwargs}
            if defaults:
                params.update(defaults)
            instance = cls(**params)
            session.add(instance)
            await session.flush()
            return instance
