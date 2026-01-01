from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from core.bot import bot
from core.decorators import GitHubEventRegistry, logger
from core.enums import GHEventType
from core.utils.bot import send_message
from database.models import Chat
from handlers.github.models.events import PingEvent


@GitHubEventRegistry.register(event=GHEventType.PING)
async def handle(event: PingEvent, session: AsyncSession) -> None:
    """Handle GitHub ping events"""

    chat_id = await _get_chat_id(event.repository.full_name, session)

    if not chat_id:
        logger.warning(f"Couldn't find chat registered for {event.repository.full_name}")
        return

    logger.info(f"Received ping event for repository: {event.repository.full_name}")

    # Build the commit message and inline buttons
    message = await _build_commit_message(event)
    buttons = await _build_inline_buttons(event)

    await send_message(
        bot=bot,
        chat_id=chat_id,
        text=message,
        url_buttons=buttons,
    )


async def _get_chat_id(repo_name: str, session: AsyncSession) -> Optional[int]:
    """Get the chat ID associated with the given repository name"""

    chat = await Chat.get_by_repo(session, repo_name)

    if not chat:
        logger.error("Failed to get chat ID for repository %s", repo_name)
        return None

    return chat.chat_id


async def _build_commit_message(event: PingEvent) -> str:
    """Build a summary message for the commits in the push event"""

    message = (
        f"🏓 <b>Ping event received from <a href='{event.repository.html_url}'>{event.repository.full_name}</a></b>\n"
        f"👤 Triggered by: <a href='{event.sender.html_url}'>{event.sender.login}</a>"
    )

    return message


async def _build_inline_buttons(event: PingEvent) -> list[tuple[str, str]]:
    """Build inline buttons for the ping event"""

    buttons = [
        ("View Repository", str(event.repository.html_url)),
    ]

    return buttons
