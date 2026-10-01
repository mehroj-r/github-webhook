import asyncio
import contextlib

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import settings
from core import get_logger
from core.decorators import distributed_lock
from core.middlewares import DatabaseMiddleware
from handlers.bot import setup_bot_handlers

logger = get_logger(__name__)

dp = Dispatcher()
dp.message.middleware(DatabaseMiddleware())

bot = Bot(
    token=settings.BOT_TOKEN,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML,
        link_preview_is_disabled=True,
    ),
)

# Background polling task (polling mode only)
polling_task: asyncio.Task | None = None


async def init_bot():
    """Initialize the bot. Returns once the bot is ready; polling runs in the background."""
    logger.info("Initializing bot")

    setup_bot_handlers(dp)

    if settings.USE_WEBHOOK:
        await _init_with_webhook()
    else:
        await _init_with_polling()


@distributed_lock("telegram_webhook_init")
async def _init_with_webhook():
    """Initialize the bot with webhook (protected by distributed lock)"""
    webhook_url = settings.telegram_webhook_url

    # Double-check if webhook is already set
    try:
        webhook_info = await bot.get_webhook_info()
        if webhook_info.url == webhook_url:
            logger.info("Webhook already set to %s. Skipping setup.", webhook_url)
            return
        logger.info("Current webhook: %s", webhook_info.url or "None")
    except Exception as e:
        logger.warning("Could not get webhook info: %s. Proceeding with setup.", e)

    # Set the webhook
    logger.info("Setting webhook to %s...", webhook_url)
    await bot.set_webhook(
        url=webhook_url,
        drop_pending_updates=True,
        secret_token=settings.WEBHOOK_SECRET or None,
    )
    logger.info("Webhook set successfully. Waiting for updates...")


async def _init_with_polling():
    """Initialize the bot with polling running as a background task"""
    global polling_task

    logger.info("Starting bot in polling mode...")
    await bot.delete_webhook(drop_pending_updates=True)
    polling_task = asyncio.create_task(dp.start_polling(bot, handle_signals=False), name="telegram-polling")


async def shutdown_bot():
    """
    Shutdown the bot gracefully.

    The Telegram webhook is intentionally left registered: with several Gunicorn workers
    (and worker recycling via max_requests) deleting it here would silently stop updates
    for the workers that are still running.
    """
    global polling_task

    logger.info("Shutting down bot...")

    if polling_task and not polling_task.done():
        polling_task.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await polling_task
        logger.info("Polling stopped")
    polling_task = None

    try:
        await bot.session.close()
        logger.info("Bot session closed")
    except Exception as e:
        logger.warning("Error closing bot session: %s", e)

    try:
        if dp.storage:
            await dp.storage.close()
            logger.info("Storage closed")
    except Exception as e:
        logger.warning("Error closing storage: %s", e)

    logger.info("Bot has been shut down successfully")
