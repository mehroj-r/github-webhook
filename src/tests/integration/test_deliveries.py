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
from database.enums import DeliveryStatus
from database.models import WebhookDelivery
from tests.payloads import REPOSITORY

SECRET = "integration-secret"


def _headers(body: bytes, delivery: str, event: str = "public") -> dict[str, str]:
    return {
        "X-GitHub-Hook-ID": "1",
        "X-GitHub-Event": event,
        "X-GitHub-Delivery": delivery,
        "User-Agent": "GitHub-Hookshot/abc",
        "X-GitHub-Hook-Installation-Target-Type": "repository",
        "X-GitHub-Hook-Installation-Target-ID": "1",
        "Content-Type": "application/json",
        "X-Hub-Signature-256": "sha256=" + hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest(),
    }


@pytest.fixture
def client():
    app = FastAPI()
    setup_api_routers(app)
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


class TestWebhookDeliveryModel:
    @pytest.mark.integration
    async def test_start_is_idempotent(self, sqlite_session_maker):
        async with sqlite_session_maker() as session:
            first, is_new = await WebhookDelivery.start(session, delivery_id="d-1", event_type="push")
            await session.commit()
            again, is_new_again = await WebhookDelivery.start(session, delivery_id="d-1", event_type="push")

        assert is_new is True
        assert is_new_again is False
        assert again.id == first.id

    @pytest.mark.integration
    async def test_finish_records_status_and_error(self, sqlite_session_maker):
        async with sqlite_session_maker() as session:
            row, _ = await WebhookDelivery.start(session, delivery_id="d-2", event_type="push")
            await row.finish(session, DeliveryStatus.FAILED, error="x" * 5000, repo_name="octocat/Hello-World", action="opened")
            await session.commit()

        async with sqlite_session_maker() as session:
            stored = await WebhookDelivery.get(session, delivery_id="d-2")
            latest = await WebhookDelivery.latest_for_repos(session, ["octocat/Hello-World"])

        assert stored.status == "failed"
        assert len(stored.error) == 2000
        assert stored.processed_at is not None
        assert [d.delivery_id for d in latest] == ["d-2"]


class TestWebhookRouteDeliveryLog:
    @pytest.mark.integration
    async def test_duplicate_delivery_is_not_reprocessed(self, client, sqlite_session_maker):
        body = json.dumps({"repository": REPOSITORY}).encode()
        handler = AsyncMock()

        with (
            patch("core.utils.github.settings") as mock_settings,
            patch("api.github.async_session_maker", sqlite_session_maker),
            patch("core.decorators.GitHubEventRegistry.get_handler", return_value=handler),
        ):
            mock_settings.GH_WEBHOOK_SECRET = SECRET
            async with client:
                first = await client.post(f"/github{settings.GH_WEBHOOK_PATH}", content=body, headers=_headers(body, "dup-1"))
                second = await client.post(f"/github{settings.GH_WEBHOOK_PATH}", content=body, headers=_headers(body, "dup-1"))

        assert first.json()["status"] == "accepted"
        assert second.json()["status"] == "duplicate"
        handler.assert_awaited_once()

        async with sqlite_session_maker() as session:
            row = await WebhookDelivery.get(session, delivery_id="dup-1")
        assert row.status == "processed"
        assert row.repo_name == "octocat/Hello-World"

    @pytest.mark.integration
    async def test_background_handler_failure_is_recorded(self, client, sqlite_session_maker):
        body = json.dumps({"repository": REPOSITORY}).encode()
        handler = AsyncMock(side_effect=RuntimeError("boom"))

        with (
            patch("core.utils.github.settings") as mock_settings,
            patch("api.github.async_session_maker", sqlite_session_maker),
            patch("core.decorators.GitHubEventRegistry.get_handler", return_value=handler),
        ):
            mock_settings.GH_WEBHOOK_SECRET = SECRET
            async with client:
                response = await client.post(f"/github{settings.GH_WEBHOOK_PATH}", content=body, headers=_headers(body, "fail-1"))

        # Acknowledged before the handler ran; the failure only shows up in the delivery log
        assert response.status_code == 200
        assert response.json()["status"] == "accepted"
        async with sqlite_session_maker() as session:
            row = await WebhookDelivery.get(session, delivery_id="fail-1")
        assert row.status == "failed"
        assert "boom" in row.error

    @pytest.mark.integration
    async def test_synchronous_handler_failure_returns_500(self, client, sqlite_session_maker):
        body = json.dumps({"repository": REPOSITORY}).encode()
        handler = AsyncMock(side_effect=RuntimeError("boom"))

        with (
            patch("core.utils.github.settings") as mock_settings,
            patch.object(settings, "WEBHOOK_PROCESS_IN_BACKGROUND", False),
            patch("api.github.async_session_maker", sqlite_session_maker),
            patch("core.decorators.GitHubEventRegistry.get_handler", return_value=handler),
        ):
            mock_settings.GH_WEBHOOK_SECRET = SECRET
            async with client:
                response = await client.post(f"/github{settings.GH_WEBHOOK_PATH}", content=body, headers=_headers(body, "fail-2"))

        assert response.status_code == 500
        async with sqlite_session_maker() as session:
            row = await WebhookDelivery.get(session, delivery_id="fail-2")
        assert row.status == "failed"
        assert "boom" in row.error
