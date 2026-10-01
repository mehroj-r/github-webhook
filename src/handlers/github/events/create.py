from html import escape

from sqlalchemy.ext.asyncio import AsyncSession

from core import get_logger
from core.decorators import GitHubEventRegistry
from core.enums import GHEventType
from core.notifications import notify, resolve_target
from handlers.github.models.events import CreateEvent

logger = get_logger(__name__)


@GitHubEventRegistry.register(event=GHEventType.CREATE)
async def handle(event: CreateEvent, session: AsyncSession) -> None:
    """Handle GitHub create events"""

    branch = event.ref_name if event.is_branch else None
    target = await resolve_target(
        session, repo_name=event.repository.full_name, event_type=GHEventType.CREATE.value, branch=branch
    )
    if not target:
        return

    logger.info("Handling create event for repository: %s", event.repository.full_name)

    # Build the message and inline buttons
    message = await _build_create_message(event=event)
    buttons = await _build_inline_buttons(event=event)

    await notify(target, text=message, url_buttons=buttons)


async def _build_create_message(event: CreateEvent) -> str:
    """Build a notification message for the create event"""

    ref_type_emoji = "🏷" if event.is_tag else "🌿"
    ref_type_text = "Tag" if event.is_tag else "Branch"

    # Build the URL to the created ref
    ref_url = f"{event.repository.html_url}/tree/{event.ref_name}"

    message = (
        f"✨ <b>New {ref_type_text} created in <a href='{event.repository.html_url}'>{escape(event.repository.full_name)}</a></b>\n"
        f"{ref_type_emoji} {ref_type_text}: <a href='{ref_url}'>{escape(event.ref_name)}</a>\n"
        f"👤 Created by: <a href='{event.sender.html_url}'>{escape(event.sender.login)}</a>"
    )

    # Add description if available
    if event.description:
        message += f"\n📄 Description: {escape(event.description)}"

    return message


async def _build_inline_buttons(event: CreateEvent):
    """Build inline URL buttons for the create event"""

    ref_url = f"{event.repository.html_url}/tree/{event.ref_name}"
    ref_type = "Tag" if event.is_tag else "Branch"

    return [
        (f"🔗 View {ref_type}", ref_url),
    ]
