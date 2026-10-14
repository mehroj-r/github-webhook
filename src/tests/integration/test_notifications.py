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


class TestBranchAndMuteCommands:
    @staticmethod
    def message(text: str) -> MagicMock:
        message = MagicMock()
        message.text = text
        message.chat.id = -100
        message.answer = AsyncMock()
        return message

    @pytest.mark.integration
    async def test_filter_branches_set_and_clear(self, sqlite_session_maker):
        from handlers.bot.settings import handle_filter_branches

        await seed(sqlite_session_maker)
        async with sqlite_session_maker() as session:
            await handle_filter_branches(self.message("/filter_branches main, release/*"), session=session)
            await session.commit()
            assert await resolve_target(session, REPO, "push", branch="feature/x") is None
            assert await resolve_target(session, REPO, "push", branch="release/2") is not None
            assert await resolve_target(session, REPO, "issues") is not None

            await handle_filter_branches(self.message("/filter_branches clear"), session=session)
            await session.commit()
            assert await resolve_target(session, REPO, "push", branch="feature/x") is not None

    @pytest.mark.integration
    async def test_mute_and_unmute(self, sqlite_session_maker):
        from handlers.bot.settings import handle_mute, handle_unmute

        await seed(sqlite_session_maker)
        muted = self.message("/mute 2h")
        async with sqlite_session_maker() as session:
            await handle_mute(muted, session=session)
            await session.commit()
            assert await resolve_target(session, REPO, "push") is None

            await handle_unmute(self.message("/unmute"), session=session)
            await session.commit()
            assert await resolve_target(session, REPO, "push") is not None

        assert "muted for 2h" in muted.answer.await_args.args[0]

    @pytest.mark.integration
    async def test_mute_rejects_bad_duration(self, sqlite_session_maker):
        from handlers.bot.settings import handle_mute

        await seed(sqlite_session_maker)
        message = self.message("/mute forever")
        async with sqlite_session_maker() as session:
            await handle_mute(message, session=session)
        assert "Give a duration" in message.answer.await_args.args[0]

    @pytest.mark.integration
    async def test_repo_must_be_named_when_several_connected(self, sqlite_session_maker):
        from handlers.bot.settings import handle_mute

        chat, _ = await seed(sqlite_session_maker)
        async with sqlite_session_maker() as session:
            await GithubRepository.create(session, title="octocat/Other", url="https://github.com/octocat/Other", chat_id=chat.id)
            await session.commit()

        ambiguous = self.message("/mute 1h")
        explicit = self.message("/mute octocat/Other 1h")
        async with sqlite_session_maker() as session:
            await handle_mute(ambiguous, session=session)
            await handle_mute(explicit, session=session)
            await session.commit()
            assert await resolve_target(session, "octocat/Other", "push") is None
            assert await resolve_target(session, REPO, "push") is not None

        assert "Several repositories" in ambiguous.answer.await_args.args[0]


class TestPauseResume:
    @pytest.mark.integration
    async def test_pause_and_resume(self, sqlite_session_maker):
        from handlers.bot.settings import handle_pause, handle_resume

        await seed(sqlite_session_maker)
        pause = TestBranchAndMuteCommands.message("/pause")
        resume = TestBranchAndMuteCommands.message("/resume")
        again = TestBranchAndMuteCommands.message("/resume")

        async with sqlite_session_maker() as session:
            await handle_pause(pause, session=session)
            await session.commit()
            assert await resolve_target(session, REPO, "push") is None

            await handle_resume(resume, session=session)
            await session.commit()
            assert await resolve_target(session, REPO, "push") is not None

            await handle_resume(again, session=session)

        assert "paused" in pause.answer.await_args.args[0]
        assert "resumed" in resume.answer.await_args.args[0]
        assert "is active" in again.answer.await_args.args[0]

    @pytest.mark.integration
    async def test_repos_lists_paused_state(self, sqlite_session_maker):
        from handlers.bot.chat import handle_repos

        await seed(sqlite_session_maker, active=False)
        message = TestBranchAndMuteCommands.message("/repos")
        async with sqlite_session_maker() as session:
            await handle_repos(message, session=session)
        assert "(paused)" in message.answer.await_args.args[0]


class TestTopicRouting:
    @staticmethod
    def topic_message(text: str, thread_id: int | None) -> MagicMock:
        message = TestBranchAndMuteCommands.message(text)
        message.is_topic_message = thread_id is not None
        message.message_thread_id = thread_id
        return message

    @pytest.mark.integration
    async def test_topic_set_and_used_for_delivery(self, sqlite_session_maker):
        from core.notifications import notify
        from handlers.bot.settings import handle_topic

        await seed(sqlite_session_maker)
        async with sqlite_session_maker() as session:
            await handle_topic(self.topic_message("/topic", thread_id=42), session=session)
            await session.commit()
            target = await resolve_target(session, REPO, "push")

        assert target is not None
        assert target.thread_id == 42

        fake_bot = MagicMock()
        fake_bot.send_message = AsyncMock()
        with patch("core.bot.bot", fake_bot):
            await notify(target, text="hello")
        assert fake_bot.send_message.await_args.kwargs["message_thread_id"] == 42

    @pytest.mark.integration
    async def test_topic_outside_forum_shows_status(self, sqlite_session_maker):
        from handlers.bot.settings import handle_topic

        await seed(sqlite_session_maker)
        message = self.topic_message("/topic", thread_id=None)
        async with sqlite_session_maker() as session:
            await handle_topic(message, session=session)
            repo = await GithubRepository.get(session, title=REPO)
        assert repo.message_thread_id is None
        assert "main chat" in message.answer.await_args.args[0]

    @pytest.mark.integration
    async def test_topic_clear(self, sqlite_session_maker):
        from handlers.bot.settings import handle_topic

        await seed(sqlite_session_maker)
        async with sqlite_session_maker() as session:
            await handle_topic(self.topic_message("/topic", thread_id=7), session=session)
            await handle_topic(self.topic_message("/topic clear", thread_id=7), session=session)
            await session.commit()
            repo = await GithubRepository.get(session, title=REPO)
        assert repo.message_thread_id is None


class TestStatus:
    @pytest.mark.integration
    async def test_status_summarises_settings(self, sqlite_session_maker):
        from datetime import UTC, datetime, timedelta

        from database.enums import DeliveryStatus
        from database.models import WebhookDelivery
        from handlers.bot.settings import handle_status

        _, repo = await seed(sqlite_session_maker, enabled_events=["push", "issues"])
        async with sqlite_session_maker() as session:
            stored = await GithubRepository.get(session, title=REPO)
            await stored.update(
                session,
                branch_filter="main",
                muted_until=datetime.now(UTC) + timedelta(hours=2),
                message_thread_id=5,
            )
            row, _ = await WebhookDelivery.start(session, delivery_id="s-1", event_type="push")
            await row.finish(session, DeliveryStatus.PROCESSED, repo_name=REPO)
            await session.commit()

        message = TestBranchAndMuteCommands.message("/status")
        async with sqlite_session_maker() as session:
            await handle_status(message, session=session)

        text = message.answer.await_args.args[0]
        assert REPO in text
        assert "events: Pushes, Issues" in text
        assert "branches: <code>main</code>" in text
        assert "muted for" in text
        assert "topic: <code>5</code>" in text
        assert "last delivery: <code>push</code> (processed)" in text

    @pytest.mark.integration
    async def test_status_without_repos(self, sqlite_session_maker):
        from handlers.bot.settings import handle_status

        message = TestBranchAndMuteCommands.message("/status")
        async with sqlite_session_maker() as session:
            await handle_status(message, session=session)
        assert "No repositories" in message.answer.await_args.args[0]
