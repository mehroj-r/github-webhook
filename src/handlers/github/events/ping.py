from sqlalchemy.ext.asyncio import AsyncSession

from core.bot import bot
from core.decorators import GitHubEventRegistry, logger
from core.enums import GHEventType
from core.utils.bot import send_message
from database.models import Chat, GithubRepository
from handlers.github.models.events import PingEvent


@GitHubEventRegistry.register(event=GHEventType.PING)
async def handle(event: PingEvent, session: AsyncSession) -> None:
    """Handle GitHub ping events"""

    logger.info(f"Received ping event for repository: {event.repository.full_name}")

    repo, created = await GithubRepository.get_or_create(
        session=session,
        title=event.repository.full_name,
        defaults={
            "url": event.repository.html_url,
            "chat_id": None,
        },
    )

    if created:
        logger.info(f"Registered new repository from ping event: {repo.title}")
        return

    # Check if repository has an associated chat
    if repo.chat_id is None:
        logger.warning(f"Repository {repo.title} has no associated chat ID")
        return

    # Get the chat associated with the repository
    chat = await Chat.get(session, id=repo.chat_id)

    if chat is None:
        logger.error(f"Chat with ID {repo.chat_id} not found for repository {repo.title}")
        return

    # Build the commit message and inline buttons
    message = await _build_commit_message(event)
    buttons = await _build_inline_buttons(event)

    await send_message(
        bot=bot,
        chat_id=chat.chat_id,
        text=message,
        url_buttons=buttons,
    )


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
