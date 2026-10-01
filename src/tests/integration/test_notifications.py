import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.notifications import resolve_target
from database.enums import ChatType
from database.models import Chat, GithubRepository
from handlers.bot.keyboards import events_callback
from handlers.bot.settings import handle_event_toggle, handle_events
from handlers.github.catalog import EVENT_KEYS

REPO = "octocat/Hello-World"


async def seed(maker, *, connected=True, active=True, chat_active=True, enabled_events=None):
    async with maker() as session:
        chat = await Chat.create(session, chat_id=-100, chat_type=ChatType.SUPERGROUP, title="t", is_active=chat_active)
        repo = await GithubRepository.create(
            session,
            title=REPO,
            url=f"https://github.com/{REPO}",
            chat_id=chat.id if connected else None,
            is_active=active,
            enabled_events=enabled_events,
        )
        await session.commit()
    return chat, repo


class TestResolveTarget:
    @pytest.mark.integration
    async def test_resolves_connected_repo(self, sqlite_session_maker):
        await seed(sqlite_session_maker)
        async with sqlite_session_maker() as session:
            target = await resolve_target(session, REPO, "push")
        assert target is not None
        assert target.chat_id == -100

    @pytest.mark.integration
    @pytest.mark.parametrize(
        "kwargs,event",
        [
            ({"connected": False}, "push"),
            ({"active": False}, "push"),
            ({"chat_active": False}, "push"),
            ({}, "star"),
            ({"enabled_events": ["issues"]}, "push"),
        ],
    )
    async def test_skips_when_not_deliverable(self, sqlite_session_maker, kwargs, event):
        await seed(sqlite_session_maker, **kwargs)
        async with sqlite_session_maker() as session:
            assert await resolve_target(session, REPO, event) is None

    @pytest.mark.integration
    async def test_unknown_repo(self, sqlite_session_maker):
        async with sqlite_session_maker() as session:
            assert await resolve_target(session, "nobody/nothing", "push") is None


class TestEventsCommand:
    @pytest.mark.integration
    async def test_single_repo_opens_keyboard(self, sqlite_session_maker):
        await seed(sqlite_session_maker)
        message = MagicMock()
        message.text = "/events"
        message.chat.id = -100
        message.answer = AsyncMock()

        async with sqlite_session_maker() as session:
            await handle_events(message, session=session)

        text, kwargs = message.answer.await_args.args[0], message.answer.await_args.kwargs
        assert REPO in text
        assert kwargs["reply_markup"].inline_keyboard[0][0].text.startswith("✅ Pushes")

    @pytest.mark.integration
    async def test_toggle_persists_and_refreshes_keyboard(self, sqlite_session_maker):
        _, repo = await seed(sqlite_session_maker)
        query = MagicMock()
        query.data = events_callback(repo.id, EVENT_KEYS.index("push"))
        query.message = MagicMock(spec=["chat", "edit_reply_markup", "edit_text"])
        query.message.chat.id = -100
        query.message.edit_reply_markup = AsyncMock()
        query.answer = AsyncMock()

        with patch("handlers.bot.settings.Message", MagicMock):
            async with sqlite_session_maker() as session:
                await handle_event_toggle(query, session=session)
                await session.commit()

        async with sqlite_session_maker() as session:
            stored = await GithubRepository.get(session, title=REPO)
        assert stored.is_event_enabled("push") is False
        assert stored.is_event_enabled("issues") is True
        query.answer.assert_awaited_once_with("Pushes disabled")
        markup = query.message.edit_reply_markup.await_args.kwargs["reply_markup"]
        assert markup.inline_keyboard[0][0].text.startswith("▫️ Pushes")

    @pytest.mark.integration
    async def test_toggle_for_repo_of_other_chat_is_rejected(self, sqlite_session_maker):
        _, repo = await seed(sqlite_session_maker)
        query = MagicMock()
        query.data = events_callback(repo.id, 0)
        query.message = MagicMock(spec=["chat", "edit_reply_markup", "edit_text"])
        query.message.chat.id = -999
        query.answer = AsyncMock()

        with patch("handlers.bot.settings.Message", MagicMock):
            async with sqlite_session_maker() as session:
                await handle_event_toggle(query, session=session)

        query.answer.assert_awaited_once_with("Repository not found.", show_alert=True)
