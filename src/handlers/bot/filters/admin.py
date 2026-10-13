from aiogram import Bot
from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from config import settings
from core import get_logger
from database import async_session_maker
from database.models import BotAdmin

logger = get_logger(__name__)

ADMIN_STATUSES = {"creator", "administrator"}
GROUP_CHAT_TYPES = {"group", "supergroup", "channel"}
ADMIN_ONLY_TEXT = "🔒 Only chat administrators can manage repository connections here."
OWNER_ONLY_TEXT = "🔒 Only the bot owner can manage bot admins."


def is_bot_owner(user_id: int | None) -> bool:
    """The owner's private chat id (MASTER_CHAT_ID) equals their user id."""
    return bool(settings.MASTER_CHAT_ID) and user_id == settings.MASTER_CHAT_ID


async def is_bot_admin(user_id: int) -> bool:
    """Owner or a runtime-managed bot admin. Filters run before middlewares, so open a session here."""
    if is_bot_owner(user_id):
        return True
    try:
        async with async_session_maker() as session:
            return await BotAdmin.is_admin(session, user_id)
    except Exception as e:
        logger.error("Could not check bot admin status of user %s: %s", user_id, e)
        return False


async def is_chat_admin(
    bot: Bot, chat_id: int, chat_type: str, user_id: int | None, sender_chat_id: int | None
) -> bool:
    """
    Decide whether the sender may manage this chat.

    Private chats are always allowed. In groups and channels the sender must be an
    administrator or creator, an anonymous admin posting as the chat itself, the bot owner or a bot admin.
    """
    if chat_type not in GROUP_CHAT_TYPES:
        return True

    # Anonymous administrators post on behalf of the chat
    if sender_chat_id is not None and sender_chat_id == chat_id:
        return True

    if user_id is None:
        return False

    if await is_bot_admin(user_id):
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


class BotOwnerFilter(BaseFilter):
    """Allow a handler only for the bot owner (MASTER_CHAT_ID)."""

    async def __call__(self, message: Message) -> bool:
        if is_bot_owner(message.from_user.id if message.from_user else None):
            return True
        await message.reply(OWNER_ONLY_TEXT)
        return False
