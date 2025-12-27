from sqlalchemy import BigInteger, String, Enum
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base, TimestampMixin
from database.enums import ChatType


class Chat(Base, TimestampMixin):

    __tablename__ = "tg_chats"

    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    title: Mapped[str | None] = mapped_column(String(255))
    chat_type: Mapped[ChatType] = mapped_column(Enum(ChatType), default=ChatType.PRIVATE)
    is_active: Mapped[bool] = mapped_column(default=True)
