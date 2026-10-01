from html import escape

from sqlalchemy.ext.asyncio import AsyncSession

from core.decorators import GitHubEventRegistry
from core.enums import GHEventType
from core.notifications import notify, resolve_target
from handlers.github.formatting import actor, labels, quote, repo_link, user_link
from handlers.github.models.events import PullRequestEvent

# Actions worth a notification; the rest (synchronize, labeled, assigned, ...) are noise for most teams
ACTION_TITLES = {
    "opened": "🆕 Pull request opened",
    "reopened": "♻️ Pull request reopened",
    "ready_for_review": "👀 Pull request ready for review",
    "converted_to_draft": "📝 Pull request converted to draft",
    "review_requested": "🙏 Review requested",
    "closed": None,  # decided by merged flag
}


@GitHubEventRegistry.register(event=GHEventType.PULL_REQUEST)
async def handle(event: PullRequestEvent, session: AsyncSession) -> None:
    """Handle GitHub pull_request events"""
    if event.action not in ACTION_TITLES or not event.repository:
        return

    pr = event.pull_request
    branch = (pr.get("base") or {}).get("ref")
    target = await resolve_target(
        session, repo_name=event.repository.full_name, event_type=GHEventType.PULL_REQUEST.value, branch=branch
    )
    if not target:
        return

    await notify(target, text=build_message(event), url_buttons=build_buttons(event))


def build_message(event: PullRequestEvent) -> str:
    pr = event.pull_request
    if event.action == "closed":
        title = "🎉 Pull request merged" if pr.get("merged") else "🚫 Pull request closed"
    else:
        title = ACTION_TITLES[event.action] or "Pull request"

    head = (pr.get("head") or {}).get("ref", "?")
    base = (pr.get("base") or {}).get("ref", "?")
    stats = ""
    if pr.get("additions") is not None:
        stats = f" [+{pr.get('additions', 0)} / -{pr.get('deletions', 0)} / {pr.get('changed_files', 0)} files]"

    message = (
        f"<b>{title}</b> in {repo_link(event)}\n"
        f"🔀 <a href='{escape(str(pr.get('html_url')))}'>#{pr.get('number')} {escape(str(pr.get('title', '')))}</a>\n"
        f"🌿 <code>{escape(str(head))}</code> → <code>{escape(str(base))}</code>{stats}\n"
        f"👤 {actor(event)}"
    )

    if event.action == "review_requested":
        reviewer = (event.model_extra or {}).get("requested_reviewer") or {}
        team = (event.model_extra or {}).get("requested_team") or {}
        who = user_link(reviewer) if reviewer else f"team <b>{escape(str(team.get('name', '?')))}</b>"
        message += f"\n🙏 Reviewer: {who}"
    elif event.action == "closed" and pr.get("merged"):
        message += f"\n✅ Merged by {user_link(pr.get('merged_by'))}"

    if pr.get("draft") and event.action != "converted_to_draft":
        message += "\n📝 Draft"
    if label_text := labels(pr.get("labels")):
        message += f"\n🏷 {label_text}"
    if event.action == "opened":
        message += quote(pr.get("body"))

    return message


def build_buttons(event: PullRequestEvent) -> list[tuple[str, str]]:
    pr = event.pull_request
    buttons = [("🔀 View Pull Request", str(pr.get("html_url")))]
    if pr.get("html_url"):
        buttons.append(("📄 Files changed", f"{pr['html_url']}/files"))
    return buttons
