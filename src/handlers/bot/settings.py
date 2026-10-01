"""Per-repository notification settings managed from Telegram."""

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from html import escape
from uuid import UUID

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from core.utils.duration import format_duration, parse_duration
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


def _matches_repo(repo: GithubRepository, text: str) -> bool:
    wanted = text.strip().rstrip("/").lower()
    return repo.title.lower() == wanted or repo.url.lower() == wanted


async def _pick_repo(
    session: AsyncSession, message: Message
) -> tuple[GithubRepository | None, Sequence[str], str | None]:
    """
    Resolve the repository a settings command applies to.

    The first argument may name the repository (title or URL). When omitted and exactly one
    repository is connected, that one is used. Returns (repo, remaining_args, error_text).
    """
    repos = await _chat_repos(session, message.chat.id)
    args = (message.text or "").split()[1:]

    if not repos:
        return None, args, "ℹ️ No repositories are connected to this chat yet. Use /connect_repo first."

    if args:
        matches = [r for r in repos if _matches_repo(r, args[0])]
        if matches:
            return matches[0], args[1:], None

    if len(repos) == 1:
        return repos[0], args, None

    return None, args, "❓ Several repositories are connected. Start the command with the repository name, see /repos."


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


@router.message(Command("filter_branches"), ChatAdminFilter())
async def handle_filter_branches(message: Message, session: AsyncSession) -> None:
    """Set, clear or show the branch filter: /filter_branches [repo] main,release/*  |  clear"""
    repo, args, error = await _pick_repo(session, message)
    if error or repo is None:
        await message.answer(error or "Repository not found.")
        return

    if not args:
        current = repo.branch_filter or "all branches"
        await message.answer(
            f"🌿 Branch filter for <b>{escape(repo.title)}</b>: <code>{escape(current)}</code>\n"
            "Usage: <code>/filter_branches [repo] main,release/*</code> or <code>/filter_branches [repo] clear</code>"
        )
        return

    value = ",".join(args)
    if value.lower() in {"clear", "all", "*"}:
        await repo.update(session, branch_filter=None)
        await message.answer(f"🌿 Branch filter cleared for <b>{escape(repo.title)}</b>. All branches are reported.")
        return

    patterns = [p.strip() for p in value.split(",") if p.strip()]
    if not patterns or len(value) > 255:
        await message.answer("❌ Provide comma-separated branch patterns, e.g. <code>main,release/*</code>.")
        return

    await repo.update(session, branch_filter=",".join(patterns))
    await message.answer(
        f"🌿 <b>{escape(repo.title)}</b> now reports only branches matching: <code>{escape(', '.join(patterns))}</code>"
    )


@router.message(Command("mute"), ChatAdminFilter())
async def handle_mute(message: Message, session: AsyncSession) -> None:
    """Silence a repository for a while: /mute [repo] 2h (default 1h)"""
    repo, args, error = await _pick_repo(session, message)
    if error or repo is None:
        await message.answer(error or "Repository not found.")
        return

    duration = parse_duration(args[0]) if args else timedelta(hours=1)
    if duration is None or duration > timedelta(days=30):
        await message.answer(
            "❌ Give a duration such as <code>30m</code>, <code>2h</code> or <code>1d</code> (max 30d)."
        )
        return

    await repo.update(session, muted_until=datetime.now(UTC) + duration)
    await message.answer(f"🔕 <b>{escape(repo.title)}</b> muted for {format_duration(duration)}.")


@router.message(Command("unmute"), ChatAdminFilter())
async def handle_unmute(message: Message, session: AsyncSession) -> None:
    repo, _, error = await _pick_repo(session, message)
    if error or repo is None:
        await message.answer(error or "Repository not found.")
        return

    if not repo.is_muted:
        await message.answer(f"🔔 <b>{escape(repo.title)}</b> is not muted.")
        return

    await repo.update(session, muted_until=None)
    await message.answer(f"🔔 <b>{escape(repo.title)}</b> unmuted.")


async def _set_active(message: Message, session: AsyncSession, active: bool) -> None:
    repo, _, error = await _pick_repo(session, message)
    if error or repo is None:
        await message.answer(error or "Repository not found.")
        return

    if repo.is_active == active:
        state = "active" if active else "already paused"
        await message.answer(f"ℹ️ <b>{escape(repo.title)}</b> is {state}.")
        return

    await repo.update(session, is_active=active)
    if active:
        await message.answer(f"▶️ <b>{escape(repo.title)}</b> resumed. Notifications are back on.")
    else:
        await message.answer(f"⏸ <b>{escape(repo.title)}</b> paused. Use /resume to turn notifications back on.")


@router.message(Command("pause"), ChatAdminFilter())
async def handle_pause(message: Message, session: AsyncSession) -> None:
    """Stop notifications for a repository until /resume (unlike /mute, without a time limit)."""
    await _set_active(message, session, active=False)


@router.message(Command("resume"), ChatAdminFilter())
async def handle_resume(message: Message, session: AsyncSession) -> None:
    await _set_active(message, session, active=True)
