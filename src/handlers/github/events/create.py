from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from core import get_logger
from core.bot import bot
from core.decorators import GitHubEventRegistry
from core.enums import GHEventType
from core.utils.bot import send_message
from database.models import Chat
from handlers.github.models.events import CreateEvent

logger = get_logger(__name__)


@GitHubEventRegistry.register(event=GHEventType.CREATE)
async def handle(event: CreateEvent, session: AsyncSession) -> None:
    """Handle GitHub create events"""

    # Get the chat ID associated with the repository
    chat_id = await _get_chat_id(repo_name=event.repository.full_name, session=session)
    if not chat_id:
        return

    logger.info("Handling create event for repository: %s", event.repository.full_name)

    # Build the message and inline buttons
    message = await _build_create_message(event=event)
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


async def _build_create_message(event: CreateEvent) -> str:
    """Build a notification message for the create event"""

    ref_type_emoji = "🏷" if event.is_tag else "🌿"
    ref_type_text = "Tag" if event.is_tag else "Branch"

    # Build the URL to the created ref
    ref_url = f"{event.repository.html_url}/tree/{event.ref_name}"

    message = (
        f"✨ <b>New {ref_type_text} created in <a href='{event.repository.html_url}'>{event.repository.full_name}</a></b>\n"
        f"{ref_type_emoji} {ref_type_text}: <a href='{ref_url}'>{event.ref_name}</a>\n"
        f"👤 Created by: <a href='{event.sender.html_url}'>{event.sender.login}</a>"
    )

    # Add description if available
    if event.description:
        message += f"\n📄 Description: {event.description}"

    return message


async def _build_inline_buttons(event: CreateEvent):
    """Build inline URL buttons for the create event"""

    ref_url = f"{event.repository.html_url}/tree/{event.ref_name}"
    ref_type = "Tag" if event.is_tag else "Branch"

    return [
        (f"🔗 View {ref_type}", ref_url),
    ]

