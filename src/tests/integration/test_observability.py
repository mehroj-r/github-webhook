import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from aiogram.exceptions import TelegramNetworkError
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from prometheus_client import REGISTRY

import api.misc as misc
from api import setup_api_routers
from config import settings
from core.metrics import record_delivery
from core.utils.bot import with_retry


def _sample(name: str, labels: dict[str, str]) -> float:
    return REGISTRY.get_sample_value(name, labels) or 0.0


@pytest.fixture
def client(sqlite_session_maker):
    app = FastAPI()
    setup_api_routers(app)
    misc._telegram_cache = None
    with patch("api.misc.async_session_maker", sqlite_session_maker):
        yield AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    misc._telegram_cache = None


def _bot(get_me: AsyncMock) -> MagicMock:
    bot = MagicMock()
    bot.get_me = get_me
    return bot


class TestHealth:
    @pytest.mark.integration
    async def test_healthy_when_database_and_telegram_respond(self, client):
        with patch("core.bot.bot", _bot(AsyncMock())):
            async with client:
                response = await client.get("/misc/health")

        assert response.status_code == 200
        assert response.json() == {"status": "healthy", "checks": {"database": "ok", "telegram": "ok"}}

    @pytest.mark.integration
    async def test_telegram_outage_is_degraded_not_failing(self, client):
        with patch("core.bot.bot", _bot(AsyncMock(side_effect=RuntimeError("down")))):
            async with client:
                response = await client.get("/misc/health")

        assert response.status_code == 200
        assert response.json()["status"] == "degraded"

    @pytest.mark.integration
    async def test_database_outage_returns_503(self, client):
        broken = MagicMock(side_effect=RuntimeError("no db"))
        with patch("api.misc.async_session_maker", broken), patch("core.bot.bot", _bot(AsyncMock())):
            async with client:
                response = await client.get("/misc/health")

        assert response.status_code == 503
        assert response.json()["checks"]["database"] == "error"

    @pytest.mark.integration
    async def test_telegram_check_is_cached(self, client):
        get_me = AsyncMock()
        with patch("core.bot.bot", _bot(get_me)):
            async with client:
                await client.get("/misc/health")
                await client.get("/misc/health")

        get_me.assert_awaited_once()


class TestMetricsEndpoint:
    @pytest.mark.integration
    async def test_exposes_prometheus_text(self, client):
        record_delivery("push", "processed")
        async with client:
            response = await client.get("/misc/metrics")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/plain")
        assert 'gh_webhook_deliveries_total{event="push",status="processed"}' in response.text

    @pytest.mark.integration
    async def test_token_required_when_configured(self, client):
        with patch.object(settings, "METRICS_TOKEN", "s3cret"):
            async with client:
                missing = await client.get("/misc/metrics")
                wrong = await client.get("/misc/metrics", headers={"Authorization": "Bearer nope"})
                ok = await client.get("/misc/metrics", headers={"Authorization": "Bearer s3cret"})

        assert missing.status_code == 401
        assert wrong.status_code == 401
        assert ok.status_code == 200


class TestInstrumentation:
    @pytest.mark.unit
    def test_record_delivery_increments_counter(self):
        labels = {"event": "issues", "status": "failed"}
        before = _sample("gh_webhook_deliveries_total", labels)
        record_delivery("issues", "failed")
        assert _sample("gh_webhook_deliveries_total", labels) == before + 1

    @pytest.mark.unit
    async def test_with_retry_observes_latency_by_method_and_outcome(self):
        ok = {"method": "send_message", "outcome": "ok"}
        failed = {"method": "edit_message", "outcome": "error"}
        ok_before = _sample("telegram_request_duration_seconds_count", ok)
        failed_before = _sample("telegram_request_duration_seconds_count", failed)

        await with_retry(AsyncMock(return_value=1), description="send_message to 1")
        with (
            patch("core.utils.bot.asyncio.sleep", AsyncMock()),
            pytest.raises(TelegramNetworkError),
        ):
            await with_retry(
                AsyncMock(side_effect=TelegramNetworkError(method=MagicMock(), message="x")),
                description="edit_message in 1",
            )

        assert _sample("telegram_request_duration_seconds_count", ok) == ok_before + 1
        assert _sample("telegram_request_duration_seconds_count", failed) == failed_before + 1
