import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database.models import Chat, GithubRepository
from handlers.bot.chat import handle_connect_repo, handle_disconnect_repo, handle_repos

REPO_URL = "https://github.com/octocat/Hello-World"


def make_message(text: str, chat_id: int = -100123, chat_type: str = "supergroup") -> MagicMock:
    message = MagicMock()
    message.text = text
    message.chat.id = chat_id
    message.chat.type = chat_type
    message.chat.title = "Dev team"
    message.chat.full_name = "Dev team"
    message.from_user.id = 777
    status_message = MagicMock()
    status_message.edit_text = AsyncMock()
    message.answer = AsyncMock(return_value=status_message)
    message.reply = AsyncMock()
    return message


def replies(message: MagicMock) -> list[str]:
    """All texts sent to the user: direct answers plus edits of the status message."""
    texts = [call.args[0] for call in message.answer.await_args_list]
    texts += [call.args[0] for call in message.answer.return_value.edit_text.await_args_list]
    return texts


@pytest.fixture
async def registered_repo(sqlite_session_maker):
    async with sqlite_session_maker() as session:
        repo = await GithubRepository.create(session, title="octocat/Hello-World", url=REPO_URL)
        await session.commit()
    return repo


class TestConnectRepo:
    @pytest.mark.integration
    async def test_connect_unregistered_repo(self, sqlite_session_maker):
        message = make_message(f"/connect_repo {REPO_URL}")
        async with sqlite_session_maker() as session:
            await handle_connect_repo(message, session=session)
        assert any("not registered" in text for text in replies(message))

    @pytest.mark.integration
    async def test_connect_creates_chat_and_links_repo(self, sqlite_session_maker, registered_repo):
        message = make_message(f"/connect_repo {REPO_URL}/")  # trailing slash + supergroup
        async with sqlite_session_maker() as session:
            await handle_connect_repo(message, session=session)
            await session.commit()

        async with sqlite_session_maker() as session:
            chat = await Chat.get(session, chat_id=-100123)
            repo = await GithubRepository.get(session, title="octocat/Hello-World")

        assert chat is not None
        assert chat.chat_type.value == "supergroup"
        assert chat.managed_by_user_id == 777
        assert repo.chat_id == chat.id
        assert any("connected successfully" in text for text in replies(message))

    @pytest.mark.integration
    async def test_connect_repo_owned_by_other_chat(self, sqlite_session_maker, registered_repo):
        async with sqlite_session_maker() as session:
            await handle_connect_repo(make_message(f"/connect_repo {REPO_URL}", chat_id=1), session=session)
            await session.commit()

        message = make_message(f"/connect_repo {REPO_URL}", chat_id=2)
        async with sqlite_session_maker() as session:
            await handle_connect_repo(message, session=session)
        assert any("already connected to another chat" in text for text in replies(message))

    @pytest.mark.integration
    async def test_invalid_url_is_rejected(self, sqlite_session_maker):
        message = make_message("/connect_repo not-a-url")
        async with sqlite_session_maker() as session:
            await handle_connect_repo(message, session=session)
        message.reply.assert_awaited_once_with("Invalid GitHub repository URL.")


class TestDisconnectAndList:
    @pytest.mark.integration
    async def test_repos_empty(self, sqlite_session_maker):
        message = make_message("/repos")
        async with sqlite_session_maker() as session:
            await handle_repos(message, session=session)
        assert "No repositories" in replies(message)[0]

    @pytest.mark.integration
    async def test_disconnect_flow(self, sqlite_session_maker, registered_repo):
        async with sqlite_session_maker() as session:
            await handle_connect_repo(make_message(f"/connect_repo {REPO_URL}"), session=session)
            await session.commit()

        listing = make_message("/repos")
        async with sqlite_session_maker() as session:
            await handle_repos(listing, session=session)
        assert "octocat/Hello-World" in replies(listing)[0]

        disconnect = make_message(f"/disconnect_repo {REPO_URL}")
        async with sqlite_session_maker() as session:
            await handle_disconnect_repo(disconnect, session=session)
            await session.commit()
        assert "Disconnected" in replies(disconnect)[0]

        async with sqlite_session_maker() as session:
            repo = await GithubRepository.get(session, title="octocat/Hello-World")
        assert repo.chat_id is None

    @pytest.mark.integration
    async def test_disconnect_from_wrong_chat(self, sqlite_session_maker, registered_repo):
        async with sqlite_session_maker() as session:
            await handle_connect_repo(make_message(f"/connect_repo {REPO_URL}", chat_id=1), session=session)
            await session.commit()

        message = make_message(f"/disconnect_repo {REPO_URL}", chat_id=2)
        async with sqlite_session_maker() as session:
            await handle_disconnect_repo(message, session=session)
        assert "not connected to this chat" in replies(message)[0]

        async with sqlite_session_maker() as session:
            repo = await GithubRepository.get(session, title="octocat/Hello-World")
        assert repo.chat_id is not None
