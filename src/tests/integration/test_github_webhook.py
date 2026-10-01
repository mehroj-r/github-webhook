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
def client():
    app = FastAPI()
    setup_api_routers(app)
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


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
        assert response.json() == {"status": "processed", "event_type": "public"}
        handler.assert_awaited_once()

    @pytest.mark.async_
    async def test_invalid_headers_return_400(self, client):
        async with client:
            response = await client.post(f"/github{settings.GH_WEBHOOK_PATH}", content=b"{}", headers={})
        assert response.status_code == 400
