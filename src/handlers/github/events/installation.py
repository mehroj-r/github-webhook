"""GitHub App installation lifecycle: register, reactivate and deactivate repositories without API calls."""

from html import escape

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core import get_logger
from core.decorators import GitHubEventRegistry
from core.enums import GHEventType
from core.notifications import NotificationTarget, notify
from core.utils.github import send_to_master
from database.models import GithubRepository
from handlers.github.models.events import InstallationEvent, InstallationRepositoriesEvent, PayloadObjects

logger = get_logger(__name__)

GITHUB_URL = "https://github.com"


@GitHubEventRegistry.register(event=GHEventType.INSTALLATION)
async def handle_installation(event: InstallationEvent, session: AsyncSession) -> dict | None:
    """Handle app installs, uninstalls and suspensions. Returns pairing codes for newly usable repositories."""
    installation_id = installation_id_of(event.installation)
    names = repo_names(event.repositories)

    match event.action:
        case "created" | "new_permissions_accepted":
            return await issue_pairing_codes(await register_repos(session, installation_id, names))
        case "unsuspend":
            for repo in await _repos_for(session, installation_id, names):
                repo.is_active = True
            return await issue_pairing_codes(await register_repos(session, installation_id, names))
        case "suspend":
            repos = await _repos_for(session, installation_id, names)
            await deactivate_repos(repos, reason="The GitHub App installation was suspended; unsuspend it to resume.")
        case "deleted":
            repos = await _repos_for(session, installation_id, names)
            await deactivate_repos(repos, reason="The GitHub App was uninstalled; reinstall it to resume.")
            for repo in repos:
                repo.installation_id = None
    return None


@GitHubEventRegistry.register(event=GHEventType.INSTALLATION_REPOSITORIES)
async def handle_installation_repositories(event: InstallationRepositoriesEvent, session: AsyncSession) -> dict | None:
    """Handle repositories being added to or removed from an existing installation."""
    installation_id = installation_id_of(event.installation)

    result = None
    if added := repo_names(event.repositories_added):
        result = await issue_pairing_codes(await register_repos(session, installation_id, added))

    if removed := repo_names(event.repositories_removed):
        repos = await _repos_for(session, None, removed)
        await deactivate_repos(repos, reason="The repository was removed from the GitHub App; add it back to resume.")
        for repo in repos:
            repo.installation_id = None
    return result


async def issue_pairing_codes(repos: list[GithubRepository]) -> dict | None:
    """Pairing codes for repositories not yet connected to a chat, also sent to the bot owner."""
    codes = {repo.title: repo.issue_pairing_code() for repo in repos if repo.chat_id is None}
    if not codes:
        return None
    lines = [f"• <b>{escape(name)}</b>: <code>{code}</code>" for name, code in codes.items()]
    await send_to_master("🔑 Pairing codes for newly installed repositories:\n" + "\n".join(lines))
    return {"pairing_codes": codes}


def installation_id_of(installation: dict) -> int:
    return int(installation["id"])


def repo_names(repositories: PayloadObjects | None) -> list[str]:
    return [r["full_name"] for r in repositories or [] if isinstance(r.get("full_name"), str)]


async def register_repos(session: AsyncSession, installation_id: int, names: list[str]) -> list[GithubRepository]:
    """Create unknown repositories (unconnected) and link/reactivate known ones."""
    repos: list[GithubRepository] = []
    for name in names:
        repo, created = await GithubRepository.get_or_create(
            session=session,
            title=name,
            defaults={"url": f"{GITHUB_URL}/{name}", "chat_id": None, "installation_id": installation_id},
        )
        if created:
            logger.info("Registered repository %s from installation %s", name, installation_id)
        else:
            repo.installation_id = installation_id
            repo.is_active = True
        repos.append(repo)
    await session.flush()
    return repos


async def deactivate_repos(repos: list[GithubRepository], reason: str) -> None:
    """Stop notifications for the repositories and tell their chats why."""
    for repo in repos:
        if not repo.is_active:
            continue
        repo.is_active = False
        logger.info("Deactivated repository %s: %s", repo.title, reason)
        if repo.chat is not None and repo.chat.is_active:
            text = build_deactivated_message(repo.title, reason)
            try:
                await notify(NotificationTarget(repo=repo, chat=repo.chat), text=text)
            except Exception as e:
                logger.warning("Could not notify chat %s about %s: %s", repo.chat.chat_id, repo.title, e)


def build_deactivated_message(repo_name: str, reason: str) -> str:
    return (
        f"⚠️ <b>Notifications stopped</b> for <a href='{GITHUB_URL}/{escape(repo_name)}'>{escape(repo_name)}</a>\n"
        f"{escape(reason)}"
    )


async def _repos_for(session: AsyncSession, installation_id: int | None, names: list[str]) -> list[GithubRepository]:
    """Repositories linked to the installation or named in the payload, with their chats loaded."""
    conditions = []
    if installation_id is not None:
        conditions.append(GithubRepository.installation_id == installation_id)
    if names:
        conditions.append(GithubRepository.title.in_(names))
    if not conditions:
        return []
    result = await session.scalars(
        select(GithubRepository).options(selectinload(GithubRepository.chat)).where(or_(*conditions))
    )
    return list(result.all())
