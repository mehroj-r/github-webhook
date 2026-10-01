from html import escape

from sqlalchemy.ext.asyncio import AsyncSession

from core.decorators import GitHubEventRegistry
from core.enums import GHEventType
from core.notifications import notify, resolve_target
from handlers.github.formatting import quote, repo_link, user_link
from handlers.github.models.events import PullRequestReviewEvent

STATE_TITLES = {
    "approved": "✅ Review approved",
    "changes_requested": "🛠 Changes requested",
    "commented": "💬 Review comment",
    "dismissed": "🚮 Review dismissed",
}


@GitHubEventRegistry.register(event=GHEventType.PULL_REQUEST_REVIEW)
async def handle(event: PullRequestReviewEvent, session: AsyncSession) -> None:
    """Handle GitHub pull_request_review events (submitted reviews only)"""
    if event.action != "submitted" or not event.repository:
        return

    branch = (event.pull_request.get("base") or {}).get("ref")
    target = await resolve_target(
        session, repo_name=event.repository.full_name, event_type=GHEventType.PULL_REQUEST_REVIEW.value, branch=branch
    )
    if not target:
        return

    await notify(
        target,
        text=build_message(event),
        url_buttons=build_buttons(event),
        session=session,
        event_type=GHEventType.PULL_REQUEST_REVIEW.value,
    )


def build_message(event: PullRequestReviewEvent) -> str:
    review = event.review
    pr = event.pull_request
    state = str(review.get("state", "commented")).lower()
    title = STATE_TITLES.get(state, f"📝 Review {state}")

    message = (
        f"<b>{title}</b> in {repo_link(event)}\n"
        f"🔀 <a href='{escape(str(pr.get('html_url')))}'>#{pr.get('number')} {escape(str(pr.get('title', '')))}</a>\n"
        f"👤 Reviewer: {user_link(review.get('user'))}"
    )
    message += quote(review.get("body"))
    return message


def build_buttons(event: PullRequestReviewEvent) -> list[tuple[str, str]]:
    url = event.review.get("html_url") or event.pull_request.get("html_url")
    return [("💬 View Review", str(url))] if url else []
