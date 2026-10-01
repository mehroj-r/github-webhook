from html import escape

from sqlalchemy.ext.asyncio import AsyncSession

from core.decorators import GitHubEventRegistry
from core.enums import GHEventType
from core.notifications import notify, resolve_target
from handlers.github.formatting import quote, repo_link, user_link
from handlers.github.models.events import IssueCommentEvent


@GitHubEventRegistry.register(event=GHEventType.ISSUE_COMMENT)
async def handle(event: IssueCommentEvent, session: AsyncSession) -> None:
    """Handle GitHub issue_comment events (new comments on issues and pull requests)"""
    if event.action != "created" or not event.repository:
        return

    target = await resolve_target(
        session, repo_name=event.repository.full_name, event_type=GHEventType.ISSUE_COMMENT.value
    )
    if not target:
        return

    await notify(target, text=build_message(event), url_buttons=build_buttons(event))


def build_message(event: IssueCommentEvent) -> str:
    issue = event.issue
    comment = event.comment
    kind = "pull request" if issue.get("pull_request") else "issue"
    icon = "🔀" if issue.get("pull_request") else "🔖"

    message = (
        f"<b>💬 New comment on {kind}</b> in {repo_link(event)}\n"
        f"{icon} <a href='{escape(str(issue.get('html_url')))}'>#{issue.get('number')} {escape(str(issue.get('title', '')))}</a>\n"
        f"👤 {user_link(comment.get('user'))}"
    )
    message += quote(comment.get("body"))
    return message


def build_buttons(event: IssueCommentEvent) -> list[tuple[str, str]]:
    url = event.comment.get("html_url") or event.issue.get("html_url")
    return [("💬 View Comment", str(url))] if url else []
