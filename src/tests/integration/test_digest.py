import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.digest import build_digest, flush_due_digests, is_due
from core.notifications import notify, resolve_target
from database.enums import ChatType
from database.models import Chat, DigestItem, GithubRepository
from handlers.bot.settings import handle_digest

REPO = "octocat/Hello-World"


async def seed(maker, digest_minutes=60):
    async with maker() as session:
        chat = await Chat.create(session, chat_id=-100, chat_type=ChatType.SUPERGROUP, title="t")
        await GithubRepository.create(
            session, title=REPO, url=f"https://github.com/{REPO}", chat_id=chat.id, digest_interval_minutes=digest_minutes
        )
        await session.commit()


def fake_bot() -> MagicMock:
    bot = MagicMock()
    bot.send_message = AsyncMock(return_value=MagicMock(message_id=1))
    return bot


def command(text: str) -> MagicMock:
    message = MagicMock()
    message.text = text
    message.chat.id = -100
    message.answer = AsyncMock()
    return message


class TestDigestQueueing:
    @pytest.mark.integration
    async def test_notify_queues_instead_of_sending(self, sqlite_session_maker):
        await seed(sqlite_session_maker)
        bot = fake_bot()
        with patch("core.bot.bot", bot):
            async with sqlite_session_maker() as session:
                target = await resolve_target(session, REPO, "push")
                result = await notify(target, "<b>Push</b>\nline", [("View", "https://x")], session=session, event_type="push")
                await session.commit()
                pending = await DigestItem.pending_for_repo(session, REPO)

        assert result is None
        bot.send_message.assert_not_awaited()
        assert len(pending) == 1
        assert pending[0].url == "https://x"

    @pytest.mark.integration
    async def test_flush_when_due_posts_digest_once(self, sqlite_session_maker):
        await seed(sqlite_session_maker, digest_minutes=30)
        bot = fake_bot()
        async with sqlite_session_maker() as session:
            for i in range(3):
                item = await DigestItem.create(session, repo_name=REPO, chat_id=-100, event_type="push", text=f"<b>Push {i}</b>\nbody", url=None)
                item.created_at = datetime.now(UTC) - timedelta(minutes=45)
            await session.commit()

        with patch("core.bot.bot", bot):
            async with sqlite_session_maker() as session:
                assert await flush_due_digests(session) == 1
                assert await flush_due_digests(session) == 0
                pending = await DigestItem.pending_for_repo(session, REPO)

        assert pending == []
        text = bot.send_message.await_args.kwargs["text"]
        assert "3 event(s)" in text
        assert "• <b>Push 0</b>" in text and "• <b>Push 2</b>" in text

    @pytest.mark.integration
    async def test_not_flushed_before_interval(self, sqlite_session_maker):
        await seed(sqlite_session_maker, digest_minutes=60)
        bot = fake_bot()
        async with sqlite_session_maker() as session:
            await DigestItem.create(session, repo_name=REPO, chat_id=-100, event_type="push", text="fresh", url=None)
            await session.commit()
        with patch("core.bot.bot", bot):
            async with sqlite_session_maker() as session:
                assert await flush_due_digests(session) == 0
        bot.send_message.assert_not_awaited()

    @pytest.mark.unit
    def test_is_due_and_build(self):
        repo = GithubRepository(title=REPO, url="https://github.com/o/r", digest_interval_minutes=10)
        now = datetime.now(UTC)
        assert is_due(repo, now - timedelta(minutes=11), now)
        assert not is_due(repo, now - timedelta(minutes=9), now)
        assert not is_due(repo, None, now)
        items = [DigestItem(repo_name=REPO, chat_id=1, event_type="push", text=f"<b>e{i}</b>", url=None) for i in range(30)]
        text = build_digest(repo, items)
        assert "30 event(s)" in text
        assert "... and 5 more" in text


class TestDigestCommand:
    @pytest.mark.integration
    async def test_enable_now_and_disable(self, sqlite_session_maker):
        await seed(sqlite_session_maker, digest_minutes=None)
        bot = fake_bot()
        with patch("core.bot.bot", bot):
            async with sqlite_session_maker() as session:
                enable = command("/digest 2h")
                await handle_digest(enable, session=session)
                await session.commit()
                repo = await GithubRepository.get(session, title=REPO)
                assert repo.digest_interval_minutes == 120
                assert "batched every 2h" in enable.answer.await_args.args[0]

                target = await resolve_target(session, REPO, "push")
                await notify(target, "<b>queued</b>", session=session, event_type="push")
                await session.commit()

                now = command("/digest now")
                await handle_digest(now, session=session)
                await session.commit()
                assert "Digest posted" in now.answer.await_args.args[0]
                bot.send_message.assert_awaited_once()

                off = command("/digest off")
                await handle_digest(off, session=session)
                await session.commit()
                repo = await GithubRepository.get(session, title=REPO)
                assert repo.digest_interval_minutes is None

    @pytest.mark.integration
    async def test_rejects_out_of_range_interval(self, sqlite_session_maker):
        await seed(sqlite_session_maker, digest_minutes=None)
        message = command("/digest 1m")
        async with sqlite_session_maker() as session:
            await handle_digest(message, session=session)
        assert "between" in message.answer.await_args.args[0]
