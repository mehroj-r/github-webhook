from html import escape

from sqlalchemy.ext.asyncio import AsyncSession

from core.decorators import GitHubEventRegistry
from core.enums import GHEventType
from core.notifications import notify, resolve_target
from handlers.github.formatting import quote, repo_link, user_link
from handlers.github.models.events import ReleaseEvent


@GitHubEventRegistry.register(event=GHEventType.RELEASE)
async def handle(event: ReleaseEvent, session: AsyncSession) -> None:
    """Handle GitHub release events (published releases and pre-releases)"""
    if event.action not in {"published", "prereleased"} or not event.repository:
        return
    # "prereleased" is always followed by "published"; avoid double posts
    if event.action == "prereleased":
        return

    target = await resolve_target(session, repo_name=event.repository.full_name, event_type=GHEventType.RELEASE.value)
    if not target:
        return

    await notify(target, text=build_message(event), url_buttons=build_buttons(event))


def build_message(event: ReleaseEvent) -> str:
    release = event.release
    kind = "Pre-release" if release.get("prerelease") else "Release"
    name = release.get("name") or release.get("tag_name") or "?"

    message = (
        f"<b>🚀 {kind} published</b> in {repo_link(event)}\n"
        f"🏷 <a href='{escape(str(release.get('html_url')))}'>{escape(str(name))}</a> (<code>{escape(str(release.get('tag_name', '')))}</code>)\n"
        f"👤 {user_link(release.get('author'))}"
    )
    message += quote(release.get("body"), limit=600)
    return message


def build_buttons(event: ReleaseEvent) -> list[tuple[str, str]]:
    url = event.release.get("html_url")
    return [("🚀 View Release", str(url))] if url else []
