import asyncio
import hmac
import time

from fastapi import APIRouter, Header, HTTPException, Response, status
from sqlalchemy import text

from config import settings
from core import get_logger
from core.metrics import render_metrics
from database import async_session_maker

logger = get_logger(__name__)

router = APIRouter(prefix="/misc", tags=["misc"])

CHECK_TIMEOUT = 3  # seconds per dependency check
TELEGRAM_CHECK_TTL = 60  # seconds; get_me is cached to stay well clear of rate limits

_telegram_cache: tuple[float, str] | None = None  # (checked_at monotonic, result)


async def _check_database() -> str:
    try:
        async with async_session_maker() as session:
            await asyncio.wait_for(session.execute(text("SELECT 1")), timeout=CHECK_TIMEOUT)
    except Exception as e:
        logger.error("Health check: database unavailable: %s", e)
        return "error"
    return "ok"


async def _check_telegram() -> str:
    global _telegram_cache
    now = time.monotonic()
    if _telegram_cache is not None and now - _telegram_cache[0] < TELEGRAM_CHECK_TTL:
        return _telegram_cache[1]

    from core.bot import bot

    try:
        await asyncio.wait_for(bot.get_me(), timeout=CHECK_TIMEOUT)
        result = "ok"
    except Exception as e:
        logger.warning("Health check: Telegram unavailable: %s", e)
        result = "error"
    _telegram_cache = (now, result)
    return result


@router.get("/health")
async def health(response: Response):
    """Health check. 503 only when the database is down; a Telegram outage reports "degraded"."""
    database, telegram = await asyncio.gather(_check_database(), _check_telegram())
    checks = {"database": database, "telegram": telegram}

    if database != "ok":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unhealthy", "checks": checks}
    if telegram != "ok":
        return {"status": "degraded", "checks": checks}
    return {"status": "healthy", "checks": checks}


@router.get("/metrics")
async def metrics(authorization: str | None = Header(default=None)) -> Response:
    """Prometheus scrape endpoint, optionally protected by METRICS_TOKEN."""
    if settings.METRICS_TOKEN:
        expected = f"Bearer {settings.METRICS_TOKEN}"
        if not authorization or not hmac.compare_digest(authorization, expected):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid metrics token")
    body, content_type = render_metrics()
    return Response(content=body, media_type=content_type)
