from fastapi import APIRouter

from config import settings
from core.logger import get_logger
from fastapi import Header, Request, Response
from aiogram.types import Update

logger = get_logger(__name__)

router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.post(settings.WEBHOOK_PATH)
async def telegram_webhook(request: Request, x_telegram_bot_api_secret_token: str = Header(None)):
    """Handle incoming webhook requests from Telegram"""
    from core.bot import bot, dp

    # Validate secret token if configured
    if settings.WEBHOOK_SECRET and x_telegram_bot_api_secret_token != settings.WEBHOOK_SECRET:
        logger.warning("Invalid webhook secret token")
        return Response(status_code=403)

    # Process the update
    try:
        update_data = await request.json()
        update = Update(**update_data)
        await dp.feed_update(bot, update)
        return Response(status_code=200)
    except Exception as e:
        logger.error(f"Error processing webhook update: {e}", exc_info=True)
        return Response(status_code=500)
