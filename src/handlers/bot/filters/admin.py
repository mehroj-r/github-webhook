from aiogram import Bot
from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from config import settings
from core import get_logger

logger = get_logger(__name__)

ADMIN_STATUSES = {"creator", "administrator"}
GROUP_CHAT_TYPES = {"group", "supergroup", "channel"}
ADMIN_ONLY_TEXT = "🔒 Only chat administrators can manage repository connections here."


async def is_chat_admin(
    bot: Bot, chat_id: int, chat_type: str, user_id: int | None, sender_chat_id: int | None
) -> bool:
    """
    Decide whether the sender may manage this chat.

    Private chats are always allowed. In groups and channels the sender must be an
    administrator or creator, an anonymous admin posting as the chat itself, or the bot owner.
    """
    if chat_type not in GROUP_CHAT_TYPES:
        return True

    # Anonymous administrators post on behalf of the chat
    if sender_chat_id is not None and sender_chat_id == chat_id:
        return True

    if user_id is None:
        return False

    # The bot owner's private chat id equals their user id
    if settings.MASTER_CHAT_ID and user_id == settings.MASTER_CHAT_ID:
        return True

    try:
        member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
    except Exception as e:
        logger.warning("Could not check admin status of user %s in chat %s: %s", user_id, chat_id, e)
        return False

    return member.status in ADMIN_STATUSES


class ChatAdminFilter(BaseFilter):
    """Allow a handler only for chat administrators (or anyone in private chats)."""

    def __init__(self, reply: bool = True) -> None:
        self.reply = reply

    async def __call__(self, event: Message | CallbackQuery, bot: Bot) -> bool:
        message = event.message if isinstance(event, CallbackQuery) else event
        if message is None or not hasattr(message, "chat"):
            return False

        user = event.from_user
        sender_chat = getattr(message, "sender_chat", None) if isinstance(event, Message) else None

        allowed = await is_chat_admin(
            bot=bot,
            chat_id=message.chat.id,
            chat_type=message.chat.type,
            user_id=user.id if user else None,
            sender_chat_id=sender_chat.id if sender_chat else None,
        )

        if not allowed and self.reply:
            if isinstance(event, CallbackQuery):
                await event.answer(ADMIN_ONLY_TEXT, show_alert=True)
            else:
                await message.reply(ADMIN_ONLY_TEXT)

        return allowed
