"""Digest mode: hold notifications back and post them as one message per interval."""

import asyncio
import contextlib
from datetime import UTC, datetime, timedelta
from html import escape

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core import get_logger
from core.utils.bot import send_message
from database import async_session_maker
from database.models import DigestItem, GithubRepository

logger = get_logger(__name__)

FLUSH_CHECK_SECONDS = 60
MAX_ITEMS_PER_DIGEST = 25

_scheduler_task: asyncio.Task | None = None


async def enqueue(
    session: AsyncSession, repo_name: str, chat_id: int, event_type: str, text: str, url: str | None
) -> None:
    """Store a notification for the next digest instead of sending it now."""
    await DigestItem.create(session, repo_name=repo_name, chat_id=chat_id, event_type=event_type, text=text, url=url)


def _headline(text: str) -> str:
    """First meaningful line of a notification, used as the digest entry."""
    for line in text.split("\n"):
        if line.strip():
            return line.strip()
    return text[:120]


def build_digest(repo: GithubRepository, items: list[DigestItem]) -> str:
    shown = items[:MAX_ITEMS_PER_DIGEST]
    lines = [f"📰 <b>Digest for <a href='{escape(repo.url)}'>{escape(repo.title)}</a></b> — {len(items)} event(s)"]
    for item in shown:
        headline = _headline(item.text)
        entry = f"• {headline}"
        if item.url:
            entry += f" <a href='{escape(item.url)}'>↗</a>"
        lines.append(entry)
    if len(items) > len(shown):
        lines.append(f"<i>... and {len(items) - len(shown)} more</i>")
    return "\n".join(lines)


def is_due(repo: GithubRepository, oldest_pending: datetime | None, now: datetime | None = None) -> bool:
    """A digest is due when the oldest held item is older than the repository's interval."""
    if oldest_pending is None or not repo.digest_interval_minutes:
        return False
    now = now or datetime.now(UTC)
    oldest = oldest_pending if oldest_pending.tzinfo else oldest_pending.replace(tzinfo=UTC)
    return now - oldest >= timedelta(minutes=repo.digest_interval_minutes)


async def flush_repo(session: AsyncSession, repo: GithubRepository, force: bool = False) -> bool:
    """Send the digest for one repository if due (or forced). Returns True when a digest was sent."""
    from core.bot import bot

    if repo.chat is None:
        return False

    oldest = await DigestItem.oldest_pending(session, repo.title)
    if not force and not is_due(repo, oldest):
        return False

    items = await DigestItem.pending_for_repo(session, repo.title)
    if not items:
        return False

    await send_message(
        bot=bot,
        chat_id=repo.chat.chat_id,
        text=build_digest(repo, items),
        message_thread_id=repo.message_thread_id,
    )
    await DigestItem.mark_flushed(session, items)
    logger.info("Sent digest with %s item(s) for %s", len(items), repo.title)
    return True


async def flush_due_digests(session: AsyncSession) -> int:
    """Flush every repository in digest mode whose window has elapsed."""
    stmt = (
        select(GithubRepository)
        .options(selectinload(GithubRepository.chat))
        .where(GithubRepository.digest_interval_minutes.is_not(None))
    )
    repos = list((await session.execute(stmt)).scalars().all())

    sent = 0
    for repo in repos:
        try:
            if await flush_repo(session, repo):
                sent += 1
                await session.commit()
        except Exception as e:
            logger.error("Failed to flush digest for %s: %s", repo.title, e, exc_info=True)
            await session.rollback()
    return sent


async def _scheduler_loop() -> None:
    from core.decorators import distributed_lock

    @distributed_lock("digest_flush")
    async def _tick() -> None:
        async with async_session_maker() as session:
            await flush_due_digests(session)

    while True:
        try:
            await _tick()
        except Exception as e:  # keep the loop alive on transient failures
            logger.error("Digest scheduler tick failed: %s", e, exc_info=True)
        await asyncio.sleep(FLUSH_CHECK_SECONDS)


def start_scheduler() -> None:
    """Start the periodic digest flusher (idempotent)."""
    global _scheduler_task
    if _scheduler_task is None or _scheduler_task.done():
        _scheduler_task = asyncio.create_task(_scheduler_loop(), name="digest-scheduler")
        logger.info("Digest scheduler started")


async def stop_scheduler() -> None:
    global _scheduler_task
    if _scheduler_task and not _scheduler_task.done():
        _scheduler_task.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await _scheduler_task
        logger.info("Digest scheduler stopped")
    _scheduler_task = None
