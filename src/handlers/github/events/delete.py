from html import escape

from sqlalchemy.ext.asyncio import AsyncSession

from core import get_logger
from core.decorators import GitHubEventRegistry
from core.enums import GHEventType
from core.notifications import notify, resolve_target
from handlers.github.models.events import DeleteEvent

logger = get_logger(__name__)


@GitHubEventRegistry.register(event=GHEventType.DELETE)
async def handle(event: DeleteEvent, session: AsyncSession) -> None:
    """Handle GitHub delete events"""

    branch = event.ref_name if event.is_branch else None
    target = await resolve_target(
        session, repo_name=event.repository.full_name, event_type=GHEventType.DELETE.value, branch=branch
    )
    if not target:
        return

    logger.info("Handling delete event for repository: %s", event.repository.full_name)

    # Build the message and inline buttons
    message = await _build_delete_message(event=event)
    buttons = await _build_inline_buttons(event=event)

    await notify(target, text=message, url_buttons=buttons, session=session, event_type=GHEventType.DELETE.value)


async def _build_delete_message(event: DeleteEvent) -> str:
    """Build a notification message for the delete event"""

    ref_type_emoji = "🏷" if event.is_tag else "🌿"
    ref_type_text = "Tag" if event.is_tag else "Branch"

    message = (
        f"🗑 <b>{ref_type_text} deleted from <a href='{event.repository.html_url}'>{escape(event.repository.full_name)}</a></b>\n"
        f"{ref_type_emoji} {ref_type_text}: <code>{escape(event.ref_name)}</code>\n"
        f"👤 Deleted by: <a href='{event.sender.html_url}'>{escape(event.sender.login)}</a>"
    )

    return message


async def _build_inline_buttons(event: DeleteEvent):
    """Build inline URL buttons for the delete event"""

    return [
        ("📂 View Repository", str(event.repository.html_url)),
    ]
