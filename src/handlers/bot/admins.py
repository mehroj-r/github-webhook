"""Bot-wide admins, managed by the owner (MASTER_CHAT_ID). Admins may manage settings in any chat."""

from html import escape

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.models import BotAdmin

from .filters import BotOwnerFilter

router = Router()

USAGE_ADD = "Usage: <code>/admin_add &lt;user_id&gt; [name]</code>, or reply to a message from that user."
USAGE_REMOVE = "Usage: <code>/admin_remove &lt;user_id&gt;</code>, or reply to a message from that user."


def parse_target(message: Message) -> tuple[int | None, str | None]:
    """User id (and display name) from the first argument, or from the replied-to message's sender."""
    args = (message.text or "").split(maxsplit=2)[1:]
    if args:
        try:
            user_id = int(args[0])
        except ValueError:
            return None, None
        return user_id, args[1] if len(args) > 1 else None

    reply = message.reply_to_message
    if reply is not None and reply.from_user is not None and not reply.from_user.is_bot:
        return reply.from_user.id, reply.from_user.full_name
    return None, None


@router.message(Command("admins"), BotOwnerFilter())
async def handle_admins(message: Message, session: AsyncSession) -> None:
    admins = await BotAdmin.all(session)
    lines = ["<b>👑 Bot admins</b>", f"• <code>{settings.MASTER_CHAT_ID}</code> — owner"]
    lines += [f"• <code>{a.user_id}</code>" + (f" — {escape(a.name)}" if a.name else "") for a in admins]
    if not admins:
        lines.append("\nNo additional admins. Add one with /admin_add.")
    await message.answer("\n".join(lines))


@router.message(Command("admin_add"), BotOwnerFilter())
async def handle_admin_add(message: Message, session: AsyncSession) -> None:
    user_id, name = parse_target(message)
    if user_id is None:
        await message.answer(USAGE_ADD)
        return
    if user_id == settings.MASTER_CHAT_ID:
        await message.answer("ℹ️ The owner already has full access.")
        return

    _, created = await BotAdmin.get_or_create(
        session,
        user_id=user_id,
        defaults={"name": name, "added_by_user_id": message.from_user.id if message.from_user else None},
    )
    if not created:
        await message.answer(f"ℹ️ <code>{user_id}</code> is already a bot admin.")
        return
    await message.answer(f"✅ <code>{user_id}</code> is now a bot admin and can manage settings in any chat.")


@router.message(Command("admin_remove"), BotOwnerFilter())
async def handle_admin_remove(message: Message, session: AsyncSession) -> None:
    user_id, _ = parse_target(message)
    if user_id is None:
        await message.answer(USAGE_REMOVE)
        return

    admin = await BotAdmin.get(session, user_id=user_id)
    if admin is None:
        await message.answer(f"ℹ️ <code>{user_id}</code> is not a bot admin.")
        return
    await admin.delete(session)
    await message.answer(f"🗑 <code>{user_id}</code> is no longer a bot admin.")
