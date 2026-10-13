from html import escape

from sqlalchemy.ext.asyncio import AsyncSession

from core import get_logger
from core.decorators import GitHubEventRegistry
from core.enums import GHEventType
from core.notifications import notify, resolve_target
from core.utils.github import send_to_master
from database.models import GithubRepository
from handlers.github.models.events import PingEvent

logger = get_logger(__name__)


@GitHubEventRegistry.register(event=GHEventType.PING)
async def handle(event: PingEvent, session: AsyncSession) -> dict | None:
    """
    Handle GitHub ping events. For a repository not yet connected to a chat, issue a pairing code and
    return it so it appears in the delivery's response body (visible under Recent Deliveries on GitHub).
    """

    if not event.repository:
        # Organization / app level hooks ping without a repository context
        logger.info("Received ping event without repository context (hook %s)", event.hook_id)
        return None

    logger.info("Received ping event for repository: %s", event.repository.full_name)

    repo, created = await GithubRepository.get_or_create(
        session=session,
        title=event.repository.full_name,
        defaults={
            "url": event.repository.html_url,
            "chat_id": None,
        },
    )

    if created or repo.chat_id is None:
        if created:
            logger.info("Registered new repository from ping event: %s", repo.title)
        return await issue_pairing(repo)

    target = await resolve_target(session, repo_name=repo.title, event_type=GHEventType.PING.value)
    if not target:
        return None

    # Build the commit message and inline buttons
    message = await _build_commit_message(event)
    buttons = await _build_inline_buttons(event)

    await notify(target, text=message, url_buttons=buttons, session=session, event_type=GHEventType.PING.value)
    return None


async def issue_pairing(repo: GithubRepository) -> dict:
    """Issue a fresh pairing code, tell the bot owner, and return the response-body fragment for GitHub."""
    code = repo.issue_pairing_code()
    command = f"/connect_repo {repo.url} {code}"
    await send_to_master(
        f"🔑 Pairing code for <b>{escape(repo.title)}</b>: <code>{code}</code>\n<code>{escape(command)}</code>"
    )
    return {"pairing_code": code, "connect_command": command}


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
