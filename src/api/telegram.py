from aiogram.types import Update
from fastapi import APIRouter, Header, Request, Response, status

from config import settings
from core import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.post(settings.WEBHOOK_PATH)
async def telegram_webhook(request: Request, x_telegram_bot_api_secret_token: str | None = Header(None)):
    """Handle incoming webhook requests from Telegram"""
    from core.bot import bot, dp

    # Validate secret token if configured
    if settings.WEBHOOK_SECRET and x_telegram_bot_api_secret_token != settings.WEBHOOK_SECRET:
        logger.warning("Invalid webhook secret token")
        return Response(status_code=status.HTTP_403_FORBIDDEN)

    # Parse the update
    try:
        update = Update.model_validate(await request.json())
    except Exception as e:
        logger.error("Invalid Telegram update payload: %s", e)
        return Response(status_code=status.HTTP_400_BAD_REQUEST)

    # Process the update. Handler failures are logged but acknowledged with 200,
    # otherwise Telegram keeps redelivering the same update and blocks the queue.
    try:
        await dp.feed_update(bot, update)
    except Exception as e:
        logger.error("Error processing webhook update %s: %s", update.update_id, e, exc_info=True)

    return Response(status_code=status.HTTP_200_OK)
