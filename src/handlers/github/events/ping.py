from html import escape

from sqlalchemy.ext.asyncio import AsyncSession

from core import get_logger
from core.bot import bot
from core.decorators import GitHubEventRegistry
from core.enums import GHEventType
from core.utils.bot import send_message
from database.models import Chat, GithubRepository
from handlers.github.models.events import PingEvent

logger = get_logger(__name__)


@GitHubEventRegistry.register(event=GHEventType.PING)
async def handle(event: PingEvent, session: AsyncSession) -> None:
    """Handle GitHub ping events"""

    if not event.repository:
        # Organization / app level hooks ping without a repository context
        logger.info("Received ping event without repository context (hook %s)", event.hook_id)
        return

    logger.info("Received ping event for repository: %s", event.repository.full_name)

    repo, created = await GithubRepository.get_or_create(
        session=session,
        title=event.repository.full_name,
        defaults={
            "url": event.repository.html_url,
            "chat_id": None,
        },
    )

    if created:
        logger.info("Registered new repository from ping event: %s", repo.title)
        return

    # Check if repository has an associated chat
    if repo.chat_id is None:
        logger.warning("Repository %s has no associated chat ID", repo.title)
        return

    # Get the chat associated with the repository
    chat = await Chat.get(session, id=repo.chat_id)

    if chat is None:
        logger.error("Chat with ID %s not found for repository %s", repo.chat_id, repo.title)
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

    assert event.repository is not None

    message = f"🏓 <b>Ping event received from <a href='{event.repository.html_url}'>{escape(event.repository.full_name)}</a></b>"
    if event.sender:
        message += f"\n👤 Triggered by: <a href='{event.sender.html_url}'>{escape(event.sender.login)}</a>"

    return message


async def _build_inline_buttons(event: PingEvent) -> list[tuple[str, str]]:
    """Build inline buttons for the ping event"""

    if not event.repository:
        return []

    return [("View Repository", str(event.repository.html_url))]
