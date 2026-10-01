"""Per-repository notification settings managed from Telegram."""

from html import escape
from uuid import UUID

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Chat, GithubRepository
from handlers.github.catalog import EVENT_KEYS, EVENT_LABELS

from .filters import ChatAdminFilter
from .keyboards import CLOSE_ACTION, EVENTS_PREFIX, REPO_PICK_PREFIX, events_keyboard, repo_picker_keyboard

router = Router()


def _events_text(repo: GithubRepository) -> str:
    return (
        f"<b>🔔 Notifications for {escape(repo.title)}</b>\n"
        "Tap an event to enable or disable it. Changes apply immediately."
    )


async def _chat_repos(session: AsyncSession, telegram_chat_id: int) -> list[GithubRepository]:
    chat = await Chat.get(session, chat_id=telegram_chat_id)
    return await GithubRepository.filter(session, chat_id=chat.id) if chat else []


async def _repo_for_chat(session: AsyncSession, telegram_chat_id: int, repo_id: UUID) -> GithubRepository | None:
    """Load a repository only if it belongs to the chat issuing the callback."""
    chat = await Chat.get(session, chat_id=telegram_chat_id)
    if chat is None:
        return None
    return await GithubRepository.get(session, id=repo_id, chat_id=chat.id)


@router.message(Command("events"), ChatAdminFilter())
async def handle_events(message: Message, session: AsyncSession) -> None:
    """Open the event toggle keyboard for a connected repository."""
    repos = await _chat_repos(session, message.chat.id)

    if not repos:
        await message.answer("ℹ️ No repositories are connected to this chat yet. Use /connect_repo first.")
        return

    # Optional repository name/url argument narrows the choice
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) == 2:
        wanted = parts[1].strip().rstrip("/").lower()
        matches = [r for r in repos if r.title.lower() == wanted or r.url.lower() == wanted]
        if not matches:
            await message.answer("❌ That repository is not connected to this chat. Use /repos to list them.")
            return
        repos = matches

    if len(repos) == 1:
        await message.answer(_events_text(repos[0]), reply_markup=events_keyboard(repos[0]))
        return

    await message.answer("Choose a repository to configure:", reply_markup=repo_picker_keyboard(repos))


@router.callback_query(F.data.startswith(f"{REPO_PICK_PREFIX}:"), ChatAdminFilter())
async def handle_repo_pick(query: CallbackQuery, session: AsyncSession) -> None:
    if not isinstance(query.message, Message) or not query.data:
        await query.answer()
        return

    repo = await _repo_for_chat(session, query.message.chat.id, UUID(hex=query.data.split(":", 1)[1]))
    if repo is None:
        await query.answer("Repository not found.", show_alert=True)
        return

    await query.message.edit_text(_events_text(repo), reply_markup=events_keyboard(repo))
    await query.answer()


@router.callback_query(F.data.startswith(f"{EVENTS_PREFIX}:"), ChatAdminFilter())
async def handle_event_toggle(query: CallbackQuery, session: AsyncSession) -> None:
    if not isinstance(query.message, Message) or not query.data:
        await query.answer()
        return

    _, repo_hex, action = query.data.split(":", 2)
    repo = await _repo_for_chat(session, query.message.chat.id, UUID(hex=repo_hex))
    if repo is None:
        await query.answer("Repository not found.", show_alert=True)
        return

    if action == CLOSE_ACTION:
        enabled = [EVENT_LABELS[k] for k in EVENT_KEYS if k in repo.enabled_event_keys]
        summary = ", ".join(enabled) if enabled else "none"
        await query.message.edit_text(f"🔔 <b>{escape(repo.title)}</b> notifies about: {escape(summary)}.")
        await query.answer()
        return

    try:
        key = EVENT_KEYS[int(action)]
    except (ValueError, IndexError):
        await query.answer("Unknown event.", show_alert=True)
        return

    await repo.update(session, enabled_events=repo.toggled_events(key))
    state = "enabled" if key in repo.enabled_event_keys else "disabled"

    await query.message.edit_reply_markup(reply_markup=events_keyboard(repo))
    await query.answer(f"{EVENT_LABELS[key]} {state}")
