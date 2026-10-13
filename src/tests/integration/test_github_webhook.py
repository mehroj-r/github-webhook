import hashlib
import hmac
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api import setup_api_routers
from config import settings

SECRET = "integration-secret"


def _headers(body: bytes, event: str = "ping", secret: str | None = SECRET) -> dict[str, str]:
    headers = {
        "X-GitHub-Hook-ID": "1",
        "X-GitHub-Event": event,
        "X-GitHub-Delivery": "delivery-1",
        "User-Agent": "GitHub-Hookshot/abc",
        "X-GitHub-Hook-Installation-Target-Type": "repository",
        "X-GitHub-Hook-Installation-Target-ID": "1",
        "Content-Type": "application/json; charset=utf-8",
    }
    if secret is not None:
        headers["X-Hub-Signature-256"] = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return headers


@pytest.fixture
def client(sqlite_session_maker):
    app = FastAPI()
    setup_api_routers(app)
    with patch("api.github.async_session_maker", sqlite_session_maker):
        yield AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


class TestGitHubWebhookRoute:
    @pytest.mark.async_
    async def test_rejects_missing_signature(self, client):
        body = json.dumps({"zen": "x"}).encode()
        with patch("core.utils.github.settings") as mock_settings:
            mock_settings.GH_WEBHOOK_SECRET = SECRET
            async with client:
                response = await client.post(
                    f"/github{settings.GH_WEBHOOK_PATH}", content=body, headers=_headers(body, secret=None)
                )
        assert response.status_code == 401

    @pytest.mark.async_
    async def test_rejects_bad_signature(self, client):
        body = json.dumps({"zen": "x"}).encode()
        with patch("core.utils.github.settings") as mock_settings:
            mock_settings.GH_WEBHOOK_SECRET = SECRET
            async with client:
                response = await client.post(
                    f"/github{settings.GH_WEBHOOK_PATH}", content=body, headers=_headers(body, secret="wrong")
                )
        assert response.status_code == 401

    @pytest.mark.async_
    async def test_valid_signature_dispatches_to_handler(self, client):
        body = json.dumps({"zen": "x", "hook_id": 1, "hook": {}}).encode()
        handler = AsyncMock()

        with (
            patch("core.utils.github.settings") as mock_settings,
            patch("core.decorators.GitHubEventRegistry.get_handler", return_value=handler),
        ):
            mock_settings.GH_WEBHOOK_SECRET = SECRET
            async with client:
                response = await client.post(
                    f"/github{settings.GH_WEBHOOK_PATH}", content=body, headers=_headers(body, event="public")
                )

        assert response.status_code == 200
        assert response.json() == {"status": "accepted", "event_type": "public"}
        handler.assert_awaited_once()

    @pytest.mark.async_
    async def test_synchronous_mode_reports_processed(self, client):
        body = json.dumps({"zen": "x", "hook_id": 1, "hook": {}}).encode()
        handler = AsyncMock()

        with (
            patch("core.utils.github.settings") as mock_settings,
            patch.object(settings, "WEBHOOK_PROCESS_IN_BACKGROUND", False),
            patch("core.decorators.GitHubEventRegistry.get_handler", return_value=handler),
        ):
            mock_settings.GH_WEBHOOK_SECRET = SECRET
            async with client:
                response = await client.post(
                    f"/github{settings.GH_WEBHOOK_PATH}", content=body, headers=_headers(body, event="public")
                )

        assert response.status_code == 200
        assert response.json() == {"status": "processed", "event_type": "public"}
        handler.assert_awaited_once()

    @pytest.mark.async_
    async def test_invalid_headers_return_400(self, client):
        async with client:
            response = await client.post(f"/github{settings.GH_WEBHOOK_PATH}", content=b"{}", headers={})
        assert response.status_code == 400


class TestPingPairing:
    @pytest.mark.integration
    async def test_ping_returns_pairing_code_and_redelivery_refreshes_it(self, client, sqlite_session_maker):
        from database.models import GithubRepository
        from tests.payloads import REPOSITORY, USER

        body = json.dumps(
            {
                "zen": "Keep it logically awesome.",
                "hook_id": 1,
                "hook": {
                    "type": "Repository",
                    "id": 1,
                    "name": "web",
                    "active": True,
                    "events": ["*"],
                    "config": {},
                    "url": "https://api.github.com/repos/octocat/Hello-World/hooks/1",
                    "created_at": "2026-10-14T00:00:00Z",
                    "updated_at": "2026-10-14T00:00:00Z",
                },
                "repository": REPOSITORY,
                "sender": USER,
            }
        ).encode()

        with (
            patch("core.utils.github.settings") as mock_settings,
            patch("core.decorators.async_session_maker", sqlite_session_maker),
        ):
            mock_settings.GH_WEBHOOK_SECRET = SECRET
            mock_settings.MASTER_CHAT_ID = None
            async with client:
                first = await client.post(f"/github{settings.GH_WEBHOOK_PATH}", content=body, headers=_headers(body))
                again = await client.post(f"/github{settings.GH_WEBHOOK_PATH}", content=body, headers=_headers(body))

        # Background mode is on by default, yet ping is answered synchronously with the code
        assert first.status_code == 200
        assert first.json()["status"] == "processed"
        assert again.json()["status"] == "processed"  # same delivery id, but pings are replayable
        first_code, second_code = first.json()["pairing_code"], again.json()["pairing_code"]
        assert first_code != second_code
        assert first.json()["connect_command"].endswith(first_code)

        async with sqlite_session_maker() as session:
            repo = await GithubRepository.get(session, title=REPOSITORY["full_name"])
        assert repo.pairing_code == second_code
