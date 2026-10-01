from html import escape

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.decorators import parse_command
from database.enums import ChatType
from database.models import Chat, GithubRepository, WebhookDelivery

from .validators.chat import ConnectRepoCommandValidator

router = Router()


@router.message(Command("connect_repo"))
@parse_command(arguments=["repo_url"], validator=ConnectRepoCommandValidator())
async def handle_connect_repo(message: Message, repo_url: str, session: AsyncSession) -> None:
    msg = await message.answer("🔗 Connecting chat to repository...")

    # Check if this repository ever pinged via webhook (URLs are stored without trailing slash)
    normalized_url = repo_url.strip().rstrip("/")
    repo = await session.scalar(
        select(GithubRepository).where(func.lower(GithubRepository.url) == normalized_url.lower())
    )

    if not repo:
        await msg.edit_text(
            "❌ This repository is not registered. "
            "Please ensure that the repository has been added via webhook before connecting."
        )
        return

    # Create chat instance if not exists
    chat, _ = await Chat.get_or_create(
        session=session,
        chat_id=message.chat.id,
        defaults={
            "chat_type": _resolve_chat_type(message.chat.type),
            "title": message.chat.title or message.chat.full_name,
        },
    )

    if not repo.chat_id:
        await repo.update(session=session, chat_id=chat.id)
        await msg.edit_text("✅ Repository connected successfully.")
        return

    if repo.chat_id != chat.id:
        await msg.edit_text(
            "❌ This repository is already connected to another chat. "
            "Please disconnect it from the current chat before connecting to a new one."
        )
        return

    await msg.edit_text("ℹ️ This chat is already connected to the specified repository.")


STATUS_ICONS = {"processed": "✅", "ignored": "⏭", "failed": "❌", "received": "⏳"}


@router.message(Command("deliveries"))
async def handle_deliveries(message: Message, session: AsyncSession) -> None:
    """Show the most recent webhook deliveries for repositories connected to this chat."""
    chat = await Chat.get(session, chat_id=message.chat.id)
    repos = await GithubRepository.filter(session, chat_id=chat.id) if chat else []

    if not repos:
        await message.answer("ℹ️ No repositories are connected to this chat yet. Use /connect_repo first.")
        return

    deliveries = await WebhookDelivery.latest_for_repos(session, [repo.title for repo in repos], limit=10)
    if not deliveries:
        await message.answer("ℹ️ No webhook deliveries recorded for the connected repositories yet.")
        return

    lines = ["<b>📬 Last webhook deliveries</b>"]
    for delivery in deliveries:
        icon = STATUS_ICONS.get(delivery.status, "•")
        event = delivery.event_type + (f"/{delivery.action}" if delivery.action else "")
        when = delivery.created_at.strftime("%Y-%m-%d %H:%M") if delivery.created_at else "-"
        line = f"{icon} <code>{when}</code> {escape(delivery.repo_name or '-')} — <code>{escape(event)}</code>"
        if delivery.error:
            line += f"\n    <i>{escape(delivery.error[:120])}</i>"
        lines.append(line)

    await message.answer("\n".join(lines))


def _resolve_chat_type(telegram_chat_type: str) -> ChatType:
    """Map a Telegram chat type onto the stored enum, falling back to GROUP for unknown kinds."""
    try:
        return ChatType(telegram_chat_type)
    except ValueError:
        return ChatType.GROUP


@router.message(F.new_chat_members)
async def handle_bot_added(message: Message):
    if not message.new_chat_members or not message.bot:
        return

    for member in message.new_chat_members:
        if member.is_bot and member.id == message.bot.id:
            await message.answer("👋 Hello! Thanks for adding me to this chat.")
