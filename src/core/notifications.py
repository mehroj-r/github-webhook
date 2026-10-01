"""Resolve where a GitHub event should be delivered and send it."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core import get_logger
from core.utils.bot import send_message
from database.models import Chat, GithubRepository

logger = get_logger(__name__)


@dataclass(slots=True)
class NotificationTarget:
    repo: GithubRepository
    chat: Chat

    @property
    def chat_id(self) -> int:
        return self.chat.chat_id

    @property
    def thread_id(self) -> int | None:
        return self.repo.message_thread_id


async def resolve_target(
    session: AsyncSession, repo_name: str, event_type: str, branch: str | None = None
) -> NotificationTarget | None:
    """
    Find the chat that should receive a notification for `repo_name` and `event_type`.

    Returns None (and logs why) when the repository is unknown, not connected, paused, muted,
    the chat is inactive, the event type is disabled, or `branch` does not match the branch filter.
    """
    repo = await session.scalar(
        select(GithubRepository).options(selectinload(GithubRepository.chat)).where(GithubRepository.title == repo_name)
    )

    if repo is None or repo.chat is None:
        logger.info("No chat configured for repository %s", repo_name)
        return None

    if not repo.is_active:
        logger.info("Repository %s is paused; skipping %s", repo_name, event_type)
        return None

    if not repo.chat.is_active:
        logger.info("Chat %s is inactive; skipping %s for %s", repo.chat.chat_id, event_type, repo_name)
        return None

    if repo.is_muted:
        logger.info("Repository %s is muted; skipping %s", repo_name, event_type)
        return None

    if not repo.is_event_enabled(event_type):
        logger.info("Event %s is disabled for repository %s", event_type, repo_name)
        return None

    if not repo.is_branch_allowed(branch):
        logger.info("Branch %s of %s does not match filter %s", branch, repo_name, repo.branch_filter)
        return None

    return NotificationTarget(repo=repo, chat=repo.chat)


async def notify(target: NotificationTarget, text: str, url_buttons: list[tuple[str, str]] | None = None) -> None:
    """Send a notification to the resolved target."""
    from core.bot import bot

    await send_message(
        bot=bot, chat_id=target.chat_id, text=text, url_buttons=url_buttons, message_thread_id=target.thread_id
    )
