import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.notifications import notify_or_edit, resolve_target
from database.enums import ChatType
from database.models import Chat, GithubRepository, SentMessage
from handlers.github.events import workflow_run
from handlers.github.models import events as m
from tests.payloads import REPOSITORY, USER

REPO = "octocat/Hello-World"
RUN = {"id": 555, "run_attempt": 1, "name": "CI", "run_number": 3, "html_url": "https://x/run", "head_branch": "main", "event": "push"}


def fake_bot(message_id: int = 100, edit_error: Exception | None = None) -> MagicMock:
    bot = MagicMock()
    sent = MagicMock()
    sent.message_id = message_id
    bot.send_message = AsyncMock(return_value=sent)
    bot.edit_message_text = AsyncMock(side_effect=edit_error) if edit_error else AsyncMock()
    return bot


async def seed(maker, enabled_events=None):
    async with maker() as session:
        chat = await Chat.create(session, chat_id=-100, chat_type=ChatType.SUPERGROUP, title="t")
        await GithubRepository.create(
            session, title=REPO, url=f"https://github.com/{REPO}", chat_id=chat.id, enabled_events=enabled_events
        )
        await session.commit()


class TestNotifyOrEdit:
    @pytest.mark.integration
    async def test_second_call_edits_first_message(self, sqlite_session_maker):
        await seed(sqlite_session_maker)
        bot = fake_bot()
        with patch("core.bot.bot", bot):
            async with sqlite_session_maker() as session:
                target = await resolve_target(session, REPO, "workflow_run")
                await notify_or_edit(session, target, key="k", text="first")
                await session.commit()
                await notify_or_edit(session, target, key="k", text="second")
                await session.commit()

        bot.send_message.assert_awaited_once()
        bot.edit_message_text.assert_awaited_once()
        assert bot.edit_message_text.await_args.kwargs["message_id"] == 100
        assert bot.edit_message_text.await_args.kwargs["text"] == "second"

    @pytest.mark.integration
    async def test_failed_edit_falls_back_to_new_message(self, sqlite_session_maker):
        await seed(sqlite_session_maker)
        bot = fake_bot(edit_error=RuntimeError("message to edit not found"))
        with patch("core.bot.bot", bot):
            async with sqlite_session_maker() as session:
                target = await resolve_target(session, REPO, "workflow_run")
                await notify_or_edit(session, target, key="k", text="first")
                await session.commit()
                bot.send_message.return_value.message_id = 200
                await notify_or_edit(session, target, key="k", text="second")
                await session.commit()
                stored = await SentMessage.find(session, REPO, "k")

        assert bot.send_message.await_count == 2
        assert stored.message_id == 200


class TestWorkflowRunLifecycle:
    @pytest.mark.integration
    async def test_queued_running_completed_share_one_message(self, sqlite_session_maker):
        await seed(sqlite_session_maker)
        bot = fake_bot()
        texts = []

        def payload(action, **run_extra):
            return {"action": action, "workflow_run": {**RUN, **run_extra}, "workflow": {"name": "CI"}, "repository": REPOSITORY, "sender": USER}

        with patch("core.bot.bot", bot):
            async with sqlite_session_maker() as session:
                for action, extra in (("requested", {}), ("in_progress", {}), ("completed", {"conclusion": "success"})):
                    event = m.WorkflowRunEvent.model_validate(payload(action, **extra))
                    await workflow_run.handle.__wrapped__(event=event, session=session)
                    await session.commit()

        texts.append(bot.send_message.await_args.kwargs["text"])
        texts += [call.kwargs["text"] for call in bot.edit_message_text.await_args_list]
        assert bot.send_message.await_count == 1
        assert bot.edit_message_text.await_count == 2
        assert "Workflow queued" in texts[0]
        assert "Workflow running" in texts[1]
        assert "✅ Workflow success" in texts[2]

    @pytest.mark.unit
    def test_message_key_includes_attempt(self):
        event = m.WorkflowRunEvent.model_validate(
            {"action": "requested", "workflow_run": {**RUN, "run_attempt": 2}, "workflow": {}, "repository": REPOSITORY, "sender": USER}
        )
        assert workflow_run.message_key(event) == "workflow_run:555:2"
