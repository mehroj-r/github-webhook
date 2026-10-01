from html import escape

from sqlalchemy.ext.asyncio import AsyncSession

from core import get_logger
from core.decorators import GitHubEventRegistry
from core.enums import GHEventType
from core.notifications import notify, resolve_target
from handlers.github.models.events import PushEvent

logger = get_logger(__name__)


@GitHubEventRegistry.register(event=GHEventType.PUSH)
async def handle(event: PushEvent, session: AsyncSession) -> None:
    """Handle GitHub push events"""

    # Skip deleted or created refs
    if any([event.deleted, event.created]):
        return

    branch = event.ref_name if event.is_branch else None
    target = await resolve_target(
        session, repo_name=event.repository.full_name, event_type=GHEventType.PUSH.value, branch=branch
    )
    if not target:
        return

    logger.info("Handling push event for repository: %s", event.repository.full_name)

    # Build the commit message and inline buttons
    message = await _build_commit_message(event=event)
    buttons = await _build_inline_buttons(event=event)

    await notify(target, text=message, url_buttons=buttons)


async def _build_commit_message(event: PushEvent) -> str:
    """Build a summary message for the commits in the push event"""

    # Build the push notification message
    commit_count = len(event.commits)
    branch_or_tag = "🏷 Tag" if event.is_tag else "🌿 Branch"

    # Build commit details (show up to 3 most recent commits)
    commit_details = []
    for commit in event.commits[-3:]:
        # Get first line of commit message
        commit_msg = commit.message.split("\n")[0]
        if len(commit_msg) > 60:
            commit_msg = commit_msg[:57] + "..."

        # Show files changed summary
        commit_details.append(f"  • <a href='{commit.url}'>{escape(commit_msg)}</a>")

    total_added, total_removed, total_modified = 0, 0, 0
    for commit in event.commits:
        total_added += len(commit.added)
        total_removed += len(commit.removed)
        total_modified += len(commit.modified)

    commits_text = "\n".join(reversed(commit_details))

    # Add "and X more" if there are more commits
    more_commits = ""
    if commit_count > 3:
        more_commits = f"\n\n<i>... and {commit_count - 3} more commit{'s' if commit_count - 3 != 1 else ''}</i>"

    # Indicate if this was a force push
    force_text = " (force push)" if event.forced else ""

    message = (
        f"🚀 <b>Push to <a href='{event.repository.html_url}'>{escape(event.repository.full_name)}</a></b>\n"
        f"{branch_or_tag}: <a href='{event.ref_url}'>{escape(event.ref_name)}</a>\n"
        f"👤 Pusher: <a href='{event.sender.html_url}'>{escape(event.sender.login)}</a>{force_text}\n"
        f"📝 {commit_count} commit{'s' if commit_count != 1 else ''} [+{total_added} / -{total_removed} / ~{total_modified}]\n\n"
        f"{commits_text}"
        f"{more_commits}"
    )

    return message


async def _build_inline_buttons(event: PushEvent):
    """Build inline URL buttons for the push event"""

    return [
        ("📊 View Changes", str(event.compare)),
    ]
