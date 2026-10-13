import sys
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from aiogram.types import Message
from aiohttp import web
from aiohttp.test_utils import TestServer

from config import settings
from core import github_api
from core.github_api import GitHubAPIError
from core.utils.bot import CALLBACK_PREFIX, build_url_keyboard, callback_button, first_url
from database.enums import ChatType
from database.models import Chat, GithubRepository
from handlers.bot.actions import handle_github_action
from handlers.github.actions import (
    APPROVE,
    MERGE,
    MERGE_CONFIRM,
    RERUN,
    pack,
    pull_request_buttons,
    unpack,
    workflow_run_buttons,
)

REPO = "octocat/Hello-World"


@pytest.fixture
def token():
    with patch.object(settings, "GH_TOKEN", "ghp_test"):
        yield


# ---- GitHub REST client against a local HTTP server ----


@pytest.fixture
async def github(token):
    """Fake GitHub API recording requests; responses are set per test via `routes`."""
    calls: list[dict] = []
    responses: dict[tuple[str, str], tuple[int, dict]] = {}

    async def handler(request: web.Request) -> web.Response:
        body = await request.json() if request.can_read_body else None
        calls.append(
            {"method": request.method, "path": request.path, "auth": request.headers.get("Authorization"), "json": body}
        )
        status, payload = responses.get((request.method, request.path), (404, {"message": "Not Found"}))
        return web.json_response(payload, status=status)

    app = web.Application()
    app.router.add_route("*", "/{tail:.*}", handler)
    server = TestServer(app)
    await server.start_server()
    with patch.object(settings, "GH_API_URL", str(server.make_url(""))):
        yield calls, responses
    await server.close()


class TestGitHubClient:
    @pytest.mark.integration
    async def test_rerun_failed_jobs(self, github):
        calls, responses = github
        responses[("POST", f"/repos/{REPO}/actions/runs/42/rerun-failed-jobs")] = (201, {})

        await github_api.rerun_failed_jobs(REPO, 42)

        assert calls[0]["auth"] == "Bearer ghp_test"

    @pytest.mark.integration
    async def test_approve_sends_review_event(self, github):
        calls, responses = github
        responses[("POST", f"/repos/{REPO}/pulls/7/reviews")] = (200, {"id": 1})

        await github_api.approve_pull_request(REPO, 7)

        assert calls[0]["json"] == {"event": "APPROVE"}

    @pytest.mark.integration
    async def test_merge_uses_configured_method_and_returns_sha(self, github):
        calls, responses = github
        responses[("PUT", f"/repos/{REPO}/pulls/7/merge")] = (200, {"sha": "abc1234def", "merged": True})

        with patch.object(settings, "GH_MERGE_METHOD", "squash"):
            sha = await github_api.merge_pull_request(REPO, 7)

        assert sha == "abc1234def"
        assert calls[0]["json"] == {"merge_method": "squash"}

    @pytest.mark.integration
    async def test_error_carries_github_message(self, github):
        _, responses = github
        responses[("PUT", f"/repos/{REPO}/pulls/7/merge")] = (405, {"message": "Pull Request is not mergeable"})

        with pytest.raises(GitHubAPIError) as exc:
            await github_api.merge_pull_request(REPO, 7)

        assert exc.value.status == 405
        assert exc.value.message == "Pull Request is not mergeable"

    @pytest.mark.integration
    async def test_non_json_error_body(self, token):
        async def bad_gateway(_: web.Request) -> web.Response:
            return web.Response(status=502, text="<html>Bad Gateway</html>", content_type="text/html")

        app = web.Application()
        app.router.add_route("*", "/{tail:.*}", bad_gateway)
        server = TestServer(app)
        await server.start_server()
        try:
            with patch.object(settings, "GH_API_URL", str(server.make_url(""))), pytest.raises(GitHubAPIError) as exc:
                await github_api.rerun_failed_jobs(REPO, 1)
        finally:
            await server.close()

        assert exc.value.status == 502

    @pytest.mark.unit
    async def test_requires_token(self):
        with patch.object(settings, "GH_TOKEN", ""), pytest.raises(GitHubAPIError):
            await github_api.rerun_failed_jobs(REPO, 1)


# ---- Buttons ----


def _repo() -> GithubRepository:
    return GithubRepository(id=uuid.uuid4(), title=REPO, url=f"https://github.com/{REPO}")


class TestButtons:
    @pytest.mark.unit
    def test_pack_roundtrip_fits_telegram_limit(self):
        repo_id = uuid.uuid4()
        data = pack(MERGE_CONFIRM, repo_id, 2**40)
        assert len(data.encode()) <= 64
        unpacked = unpack(data)
        assert unpacked is not None
        assert (unpacked.action, unpacked.repo_id, unpacked.number) == (MERGE_CONFIRM, repo_id, 2**40)

    @pytest.mark.unit
    @pytest.mark.parametrize("data", ["gh:rerun", "ev:x:y:z", "gh:rerun:not-hex:1", "gh:rerun:" + "a" * 32 + ":x"])
    def test_unpack_rejects_garbage(self, data):
        assert unpack(data) is None

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "action,conclusion,expected",
        [("completed", "failure", 1), ("completed", "timed_out", 1), ("completed", "success", 0), ("in_progress", None, 0)],
    )
    def test_rerun_button_only_for_failed_runs(self, token, action, conclusion, expected):
        buttons = workflow_run_buttons(_repo(), action, {"id": 99, "conclusion": conclusion})
        assert len(buttons) == expected

    @pytest.mark.unit
    def test_pr_buttons_for_open_ready_prs(self, token):
        repo = _repo()
        buttons = pull_request_buttons(repo, "opened", {"number": 7, "state": "open", "draft": False})
        assert [unpack(target.removeprefix(CALLBACK_PREFIX)).action for _, target in buttons] == [APPROVE, MERGE]

        assert pull_request_buttons(repo, "opened", {"number": 7, "state": "open", "draft": True}) == []
        assert pull_request_buttons(repo, "closed", {"number": 7, "state": "closed"}) == []

    @pytest.mark.unit
    def test_no_buttons_without_token(self):
        with patch.object(settings, "GH_TOKEN", ""):
            assert workflow_run_buttons(_repo(), "completed", {"id": 1, "conclusion": "failure"}) == []

    @pytest.mark.unit
    def test_keyboard_puts_callbacks_in_one_bottom_row(self):
        action = callback_button("Go", "gh:x")
        assert action is not None
        keyboard = build_url_keyboard([("View", "https://example.com"), action, ("Other", "https://example.org")])

        rows = keyboard.inline_keyboard
        assert [b.url for b in rows[0] + rows[1]] == ["https://example.com", "https://example.org"]
        assert rows[2][0].callback_data == "gh:x"
        assert first_url([action, ("View", "https://example.com")]) == "https://example.com"

    @pytest.mark.unit
    def test_callback_button_rejects_oversized_data(self):
        assert callback_button("x", "y" * 65) is None


# ---- Callback handler ----


async def seed(maker) -> GithubRepository:
    async with maker() as session:
        chat = await Chat.create(session, chat_id=-100, chat_type=ChatType.SUPERGROUP, title="t")
        repo = await GithubRepository.create(session, title=REPO, url=f"https://github.com/{REPO}", chat_id=chat.id)
        await session.commit()
    return repo


def make_query(data: str, chat_id: int = -100) -> MagicMock:
    message = MagicMock(spec=Message)
    message.chat = MagicMock()
    message.chat.id = chat_id
    message.reply = AsyncMock()
    message.edit_text = AsyncMock()
    query = MagicMock()
    query.data = data
    query.message = message
    query.from_user.id = 5
    query.from_user.username = "ada"
    query.answer = AsyncMock()
    return query


class TestActionCallbacks:
    @pytest.mark.integration
    async def test_rerun_calls_github_and_reports(self, sqlite_session_maker):
        repo = await seed(sqlite_session_maker)
        query = make_query(pack(RERUN, repo.id, 42))

        with patch("handlers.bot.actions.github_api.rerun_failed_jobs", AsyncMock()) as rerun:
            async with sqlite_session_maker() as session:
                await handle_github_action(query, session=session)

        rerun.assert_awaited_once_with(REPO, 42)
        assert "@ada" in query.message.reply.await_args.args[0]

    @pytest.mark.integration
    async def test_button_from_another_chat_is_refused(self, sqlite_session_maker):
        repo = await seed(sqlite_session_maker)
        query = make_query(pack(APPROVE, repo.id, 7), chat_id=-999)

        with patch("handlers.bot.actions.github_api.approve_pull_request", AsyncMock()) as approve:
            async with sqlite_session_maker() as session:
                await handle_github_action(query, session=session)

        approve.assert_not_awaited()
        assert query.answer.await_args.kwargs["show_alert"] is True

    @pytest.mark.integration
    async def test_merge_asks_for_confirmation_first(self, sqlite_session_maker):
        repo = await seed(sqlite_session_maker)
        query = make_query(pack(MERGE, repo.id, 7))

        with patch("handlers.bot.actions.github_api.merge_pull_request", AsyncMock()) as merge:
            async with sqlite_session_maker() as session:
                await handle_github_action(query, session=session)

        merge.assert_not_awaited()
        keyboard = query.message.reply.await_args.kwargs["reply_markup"]
        assert unpack(keyboard.inline_keyboard[0][0].callback_data).action == MERGE_CONFIRM

    @pytest.mark.integration
    async def test_confirmed_merge_edits_prompt(self, sqlite_session_maker):
        repo = await seed(sqlite_session_maker)
        query = make_query(pack(MERGE_CONFIRM, repo.id, 7))

        with patch("handlers.bot.actions.github_api.merge_pull_request", AsyncMock(return_value="abc1234def")):
            async with sqlite_session_maker() as session:
                await handle_github_action(query, session=session)

        text = query.message.edit_text.await_args.args[0]
        assert "merged by @ada" in text
        assert "abc1234" in text

    @pytest.mark.integration
    async def test_github_error_is_shown_as_alert(self, sqlite_session_maker):
        repo = await seed(sqlite_session_maker)
        query = make_query(pack(MERGE_CONFIRM, repo.id, 7))
        error = GitHubAPIError(405, "Pull Request is not mergeable")

        with patch("handlers.bot.actions.github_api.merge_pull_request", AsyncMock(side_effect=error)):
            async with sqlite_session_maker() as session:
                await handle_github_action(query, session=session)

        assert "not mergeable" in query.answer.await_args.args[0]
        assert query.answer.await_args.kwargs["show_alert"] is True
        query.message.edit_text.assert_not_awaited()
