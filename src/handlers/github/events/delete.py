from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from core import get_logger
from core.bot import bot
from core.decorators import GitHubEventRegistry
from core.enums import GHEventType
from core.utils.bot import send_message
from database.models import Chat
from handlers.github.models.events import DeleteEvent

logger = get_logger(__name__)


@GitHubEventRegistry.register(event=GHEventType.DELETE)
async def handle(event: DeleteEvent, session: AsyncSession) -> None:
    """Handle GitHub delete events"""

    # Get the chat ID associated with the repository
    chat_id = await _get_chat_id(repo_name=event.repository.full_name, session=session)
    if not chat_id:
        return

    logger.info("Handling delete event for repository: %s", event.repository.full_name)

    # Build the message and inline buttons
    message = await _build_delete_message(event=event)
    buttons = await _build_inline_buttons(event=event)

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


async def _build_delete_message(event: DeleteEvent) -> str:
    """Build a notification message for the delete event"""

    ref_type_emoji = "🏷" if event.is_tag else "🌿"
    ref_type_text = "Tag" if event.is_tag else "Branch"

    message = (
        f"🗑 <b>{ref_type_text} deleted from <a href='{event.repository.html_url}'>{event.repository.full_name}</a></b>\n"
        f"{ref_type_emoji} {ref_type_text}: <code>{event.ref_name}</code>\n"
        f"👤 Deleted by: <a href='{event.sender.html_url}'>{event.sender.login}</a>"
    )

    return message


async def _build_inline_buttons(event: DeleteEvent):
    """Build inline URL buttons for the delete event"""

    return [
        ("📂 View Repository", str(event.repository.html_url)),
    ]

