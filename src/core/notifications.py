"""Resolve where a GitHub event should be delivered and send it."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core import get_logger
from core.utils.bot import edit_message, send_message
from database.models import Chat, GithubRepository, SentMessage

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


async def notify(target: NotificationTarget, text: str, url_buttons: list[tuple[str, str]] | None = None):
    """Send a notification to the resolved target. Returns the sent Telegram message."""
    from core.bot import bot

    return await send_message(
        bot=bot, chat_id=target.chat_id, text=text, url_buttons=url_buttons, message_thread_id=target.thread_id
    )


async def notify_or_edit(
    session: AsyncSession,
    target: NotificationTarget,
    key: str,
    text: str,
    url_buttons: list[tuple[str, str]] | None = None,
) -> None:
    """
    Edit the message previously sent for `key` (per repository), or send a new one and remember it.

    Used for objects with a lifecycle (workflow runs) so one message is updated instead of
    posting once per state change. Falls back to a new message when editing fails, e.g. because
    the original was deleted or is too old.
    """
    from core.bot import bot

    previous = await SentMessage.find(session, repo_name=target.repo.title, key=key)
    if previous and previous.chat_id == target.chat_id:
        try:
            await edit_message(
                bot, chat_id=previous.chat_id, message_id=previous.message_id, text=text, url_buttons=url_buttons
            )
            return
        except Exception as e:
            logger.warning("Could not edit message %s for %s/%s: %s", previous.message_id, target.repo.title, key, e)

    sent = await notify(target, text=text, url_buttons=url_buttons)
    await SentMessage.remember(
        session, repo_name=target.repo.title, key=key, chat_id=target.chat_id, message_id=sent.message_id
    )
