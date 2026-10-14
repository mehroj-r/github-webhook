import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.enums import GHEventType
from database.enums import ChatType
from database.models import Chat, GithubRepository
from handlers.github.events import installation
from handlers.github.models.events import InstallationEvent, InstallationRepositoriesEvent
from tests.payloads import USER

INSTALLATION = {"id": 777, "account": {"login": "octocat"}}
REPO = "octocat/Hello-World"
OTHER = "octocat/Spoon-Knife"


def _repos(*names: str) -> list[dict]:
    return [{"id": i, "name": n.split("/")[1], "full_name": n, "private": False} for i, n in enumerate(names)]


def installation_event(action: str, *names: str) -> InstallationEvent:
    return InstallationEvent.model_validate(
        {"action": action, "installation": INSTALLATION, "repositories": _repos(*names), "sender": USER}
    )


def repositories_event(action: str, added: tuple = (), removed: tuple = ()) -> InstallationRepositoriesEvent:
    return InstallationRepositoriesEvent.model_validate(
        {
            "action": action,
            "installation": INSTALLATION,
            "repository_selection": "selected",
            "repositories_added": _repos(*added),
            "repositories_removed": _repos(*removed),
            "sender": USER,
        }
    )


async def _get(maker, name: str) -> GithubRepository | None:
    async with maker() as session:
        return await GithubRepository.get(session, title=name)


async def _connect(maker, name: str) -> None:
    async with maker() as session:
        chat = await Chat.create(session, chat_id=-100, chat_type=ChatType.SUPERGROUP, title="t")
        repo = await GithubRepository.get(session, title=name)
        assert repo is not None
        repo.chat_id = chat.id
        await session.commit()


@pytest.fixture
def run(sqlite_session_maker):
    """Call a registered handler the way the webhook route does (own session, commit on success)."""

    async def _run(event_type: GHEventType, event) -> None:
        from core.decorators import GitHubEventRegistry

        handler = GitHubEventRegistry.get_handler(event_type)
        assert handler is not None
        await handler(event=event)

    with patch("core.decorators.async_session_maker", sqlite_session_maker):
        yield _run


@pytest.fixture(autouse=True)
def no_owner():
    from config import settings

    with patch.object(settings, "MASTER_CHAT_ID", None):
        yield


@pytest.fixture
def bot():
    mock = MagicMock()
    mock.send_message = AsyncMock()
    with patch("core.bot.bot", mock):
        yield mock


class TestInstallation:
    @pytest.mark.integration
    async def test_created_registers_unconnected_repos(self, run, sqlite_session_maker):
        await run(GHEventType.INSTALLATION, installation_event("created", REPO, OTHER))

        repo = await _get(sqlite_session_maker, REPO)
        assert repo is not None
        assert repo.url == f"https://github.com/{REPO}"
        assert repo.installation_id == 777
        assert repo.chat_id is None
        assert await _get(sqlite_session_maker, OTHER) is not None

    @pytest.mark.integration
    async def test_created_links_existing_repo(self, run, sqlite_session_maker):
        async with sqlite_session_maker() as session:
            await GithubRepository.create(session, title=REPO, url=f"https://github.com/{REPO}", is_active=False)
            await session.commit()

        await run(GHEventType.INSTALLATION, installation_event("created", REPO))

        repo = await _get(sqlite_session_maker, REPO)
        assert repo.installation_id == 777
        assert repo.is_active is True

    @pytest.mark.integration
    async def test_deleted_deactivates_by_installation_and_notifies_chat(self, run, sqlite_session_maker, bot):
        await run(GHEventType.INSTALLATION, installation_event("created", REPO))
        await _connect(sqlite_session_maker, REPO)

        # Uninstall payloads may omit the repository list; the stored installation id is enough
        await run(GHEventType.INSTALLATION, installation_event("deleted"))

        repo = await _get(sqlite_session_maker, REPO)
        assert repo.is_active is False
        assert repo.installation_id is None
        bot.send_message.assert_awaited_once()
        assert "uninstalled" in bot.send_message.await_args.kwargs["text"]

    @pytest.mark.integration
    async def test_suspend_and_unsuspend(self, run, sqlite_session_maker, bot):
        await run(GHEventType.INSTALLATION, installation_event("created", REPO))

        await run(GHEventType.INSTALLATION, installation_event("suspend"))
        assert (await _get(sqlite_session_maker, REPO)).is_active is False

        await run(GHEventType.INSTALLATION, installation_event("unsuspend"))
        repo = await _get(sqlite_session_maker, REPO)
        assert repo.is_active is True
        assert repo.installation_id == 777
        bot.send_message.assert_not_awaited()  # repo was never connected to a chat


class TestInstallationPairing:
    @pytest.mark.integration
    async def test_new_repos_get_codes_and_owner_is_told(self, run, sqlite_session_maker, bot):
        from config import settings

        with patch.object(settings, "MASTER_CHAT_ID", 42):
            from core.decorators import GitHubEventRegistry

            with patch("core.decorators.async_session_maker", sqlite_session_maker):
                handler = GitHubEventRegistry.get_handler(GHEventType.INSTALLATION)
                result = await handler(event=installation_event("created", REPO))

        repo = await _get(sqlite_session_maker, REPO)
        assert result == {"pairing_codes": {REPO: repo.pairing_code}}
        assert bot.send_message.await_args.kwargs["chat_id"] == 42
        assert repo.pairing_code in bot.send_message.await_args.kwargs["text"]

    @pytest.mark.integration
    async def test_connected_repos_get_no_code(self, run, sqlite_session_maker):
        await run(GHEventType.INSTALLATION, installation_event("created", REPO))
        await _connect(sqlite_session_maker, REPO)

        from core.decorators import GitHubEventRegistry

        handler = GitHubEventRegistry.get_handler(GHEventType.INSTALLATION_REPOSITORIES)
        assert await handler(event=repositories_event("added", added=(REPO,))) is None


class TestInstallationRepositories:
    @pytest.mark.integration
    async def test_added_and_removed(self, run, sqlite_session_maker, bot):
        await run(GHEventType.INSTALLATION_REPOSITORIES, repositories_event("added", added=(REPO,)))
        assert (await _get(sqlite_session_maker, REPO)).installation_id == 777

        await _connect(sqlite_session_maker, REPO)
        await run(GHEventType.INSTALLATION_REPOSITORIES, repositories_event("removed", removed=(REPO,)))

        repo = await _get(sqlite_session_maker, REPO)
        assert repo.is_active is False
        assert repo.installation_id is None
        assert "removed from the GitHub App" in bot.send_message.await_args.kwargs["text"]

        await run(GHEventType.INSTALLATION_REPOSITORIES, repositories_event("added", added=(REPO,)))
        assert (await _get(sqlite_session_maker, REPO)).is_active is True


class TestHelpers:
    @pytest.mark.unit
    def test_repo_names_skips_malformed_entries(self):
        assert installation.repo_names([{"full_name": REPO}, {"name": "x"}, {"full_name": None}]) == [REPO]
        assert installation.repo_names(None) == []

    @pytest.mark.unit
    def test_deactivated_message_escapes_html(self):
        text = installation.build_deactivated_message("a/<b>", "gone")
        assert "&lt;b&gt;" in text
        assert "gone" in text
