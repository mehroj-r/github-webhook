from html import escape

from sqlalchemy.ext.asyncio import AsyncSession

from core.decorators import GitHubEventRegistry
from core.enums import GHEventType
from core.notifications import notify, resolve_target
from handlers.github.formatting import actor, labels, quote, repo_link, user_link
from handlers.github.models.events import IssuesEvent

ACTION_TITLES = {
    "opened": "🐛 Issue opened",
    "closed": "✅ Issue closed",
    "reopened": "♻️ Issue reopened",
    "assigned": "👤 Issue assigned",
    "transferred": "📦 Issue transferred",
}


@GitHubEventRegistry.register(event=GHEventType.ISSUES)
async def handle(event: IssuesEvent, session: AsyncSession) -> None:
    """Handle GitHub issues events"""
    if event.action not in ACTION_TITLES or not event.repository:
        return

    target = await resolve_target(session, repo_name=event.repository.full_name, event_type=GHEventType.ISSUES.value)
    if not target:
        return

    await notify(
        target,
        text=build_message(event),
        url_buttons=build_buttons(event),
        session=session,
        event_type=GHEventType.ISSUES.value,
    )


def build_message(event: IssuesEvent) -> str:
    issue = event.issue
    message = (
        f"<b>{ACTION_TITLES[event.action]}</b> in {repo_link(event)}\n"
        f"🔖 <a href='{escape(str(issue.get('html_url')))}'>#{issue.get('number')} {escape(str(issue.get('title', '')))}</a>\n"
        f"👤 {actor(event)}"
    )

    if event.action == "assigned":
        message += f"\n➡️ Assignee: {user_link(event.assignee or issue.get('assignee'))}"
    if event.action == "closed" and issue.get("state_reason"):
        message += f"\n📌 Reason: <code>{escape(str(issue['state_reason']))}</code>"
    if label_text := labels(issue.get("labels")):
        message += f"\n🏷 {label_text}"
    if event.action == "opened":
        message += quote(issue.get("body"))

    return message


def build_buttons(event: IssuesEvent) -> list[tuple[str, str]]:
    url = event.issue.get("html_url")
    return [("🔖 View Issue", str(url))] if url else []
