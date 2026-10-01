from html import escape

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.decorators import parse_command
from database.enums import ChatType
from database.models import Chat, GithubRepository, WebhookDelivery

from .filters import ChatAdminFilter
from .texts import HELP_TEXT
from .validators.chat import ConnectRepoCommandValidator, DisconnectRepoCommandValidator

router = Router()


@router.message(Command("connect_repo"), ChatAdminFilter())
@parse_command(arguments=["repo_url"], validator=ConnectRepoCommandValidator())
async def handle_connect_repo(message: Message, repo_url: str, session: AsyncSession) -> None:
    msg = await message.answer("🔗 Connecting chat to repository...")

    # Check if this repository ever pinged via webhook
    repo = await _find_repo_by_url(session, repo_url)

    if not repo:
        await msg.edit_text(
            "❌ This repository is not registered. "
            "Please ensure that the repository has been added via webhook before connecting."
        )
        return

    # Create chat instance if not exists and remember who manages it
    chat, _ = await Chat.get_or_create(
        session=session,
        chat_id=message.chat.id,
        defaults={
            "chat_type": _resolve_chat_type(message.chat.type),
            "title": message.chat.title or message.chat.full_name,
        },
    )
    if message.from_user and chat.managed_by_user_id != message.from_user.id:
        await chat.update(session=session, managed_by_user_id=message.from_user.id)

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


@router.message(Command("disconnect_repo"), ChatAdminFilter())
@parse_command(arguments=["repo_url"], validator=DisconnectRepoCommandValidator())
async def handle_disconnect_repo(message: Message, repo_url: str, session: AsyncSession) -> None:
    repo = await _find_repo_by_url(session, repo_url)
    chat = await Chat.get(session, chat_id=message.chat.id)

    if not repo or not chat or repo.chat_id != chat.id:
        await message.answer("ℹ️ This repository is not connected to this chat.")
        return

    await repo.update(session=session, chat_id=None)
    await message.answer(f"🔌 Disconnected <b>{escape(repo.title)}</b>. Notifications for it will stop.")


@router.message(Command("repos"))
async def handle_repos(message: Message, session: AsyncSession) -> None:
    """List repositories connected to this chat."""
    chat = await Chat.get(session, chat_id=message.chat.id)
    repos = await GithubRepository.filter(session, chat_id=chat.id) if chat else []

    if not repos:
        await message.answer("ℹ️ No repositories are connected to this chat yet. Use /connect_repo to add one.")
        return

    lines = ["<b>📚 Connected repositories</b>"]
    for repo in sorted(repos, key=lambda r: r.title.lower()):
        state = "" if repo.is_active else " (paused)"
        lines.append(f"• <a href='{repo.url}'>{escape(repo.title)}</a>{state}")

    await message.answer("\n".join(lines))


@router.message(Command("help"))
async def handle_help(message: Message) -> None:
    await message.answer(HELP_TEXT)


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


async def _find_repo_by_url(session: AsyncSession, repo_url: str) -> GithubRepository | None:
    """Look a registered repository up by URL, ignoring case and trailing slashes."""
    normalized_url = repo_url.strip().rstrip("/")
    return await session.scalar(
        select(GithubRepository).where(func.lower(GithubRepository.url) == normalized_url.lower())
    )


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
