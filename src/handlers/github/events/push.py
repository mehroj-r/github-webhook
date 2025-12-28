from sqlalchemy.ext.asyncio import AsyncSession

from core import get_logger
from core.bot import bot
from core.decorators import GitHubEventRegistry
from core.enums import GHEventType
from core.utils.bot import send_message
from database.models import GithubRepository, Chat
from handlers.github.models.events import PushEvent

logger = get_logger(__name__)


@GitHubEventRegistry.register(event=GHEventType.PUSH)
async def handle_push_event(event: PushEvent, session: AsyncSession):
    """Handle GitHub push events"""

    repo = await GithubRepository.get(session=session, title=event.repository.full_name)

    if repo is None:
        logger.warning("Repository %s not found in database. Ignoring push event.", event.repository.full_name)
        return

    logger.info("Handling push event for repository: %s", event.repository.full_name)

    chat = await Chat.get(session=session, id=repo.chat_id)

    if chat is None:
        logger.warning("Chat with ID %s not found in database. Cannot send push notification.", event.chat_id)
        return

    # Build the push notification message
    commit_count = len(event.commits)
    branch_or_tag = "🏷 Tag" if event.is_tag else "🌿 Branch"

    # Build commit details (show up to 3 commits)
    commit_details = []
    for commit in event.commits[commit_count - 3 :]:
        # Get first line of commit message
        commit_msg = commit.message.split("\n")[0]
        if len(commit_msg) > 60:
            commit_msg = commit_msg[:57] + "..."

        # Show files changed summary
        commit_details.append(f"  • <a href='{commit.url}'>{commit_msg}</a>")

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

    message = (
        f"🚀 <b>Push to <a href='{event.repository.html_url}'>{event.repository.full_name}</a></b>\n"
        f"{branch_or_tag}: <a href='{event.ref_url}'>{event.ref_name}</a>\n"
        f"👤 Pusher: <a href='{event.sender.html_url}'>{event.sender.login}</a>\n"
        f"📝 {commit_count} commit{'s' if commit_count != 1 else ''} [+{total_added} / -{total_removed} / ~{total_modified}]\n\n"
        f"{commits_text}"
        f"{more_commits}"
    )

    # URL buttons
    buttons = [
        ("📊 View Changes", str(event.compare)),
    ]

    await send_message(
        bot=bot,
        chat_id=chat.chat_id,
        text=message,
        url_buttons=buttons,
    )
