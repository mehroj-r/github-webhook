from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from handlers import register_all_handlers
from config import settings
from core import get_logger

logger = get_logger(__name__)

dp = Dispatcher()

bot = Bot(
    token=settings.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)


async def init_bot():
    """Initialize the bot"""
    logger.info("Initializing bot")

    register_all_handlers(dp)

    match settings.USE_WEBHOOK:
        case True:
            await _init_with_webhook()
        case False:
            await _init_with_polling()


async def _init_with_webhook():
    """Initialize the bot with webhook"""
    logger.info(f"Setting webhook to {settings.WEBHOOK_URL}")
    webhook_url = settings.WEBHOOK_URL + "/telegram" + settings.WEBHOOK_PATH
    await bot.set_webhook(
        url=webhook_url,
        drop_pending_updates=True,
        secret_token=settings.WEBHOOK_SECRET,
    )
    logger.info("Webhook set successfully. Waiting for updates...")


async def _init_with_polling():
    """Initialize the bot with polling"""
    logger.info("Starting bot in polling mode...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


async def shutdown_bot():
    """
    Shutdown the bot gracefully.
    """
    logger.info("Shutting down bot...")

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhook deleted")
    except Exception as e:
        logger.warning(f"Error deleting webhook: {e}")

    try:
        await bot.session.close()
        logger.info("Bot session closed")
    except Exception as e:
        logger.warning(f"Error closing bot session: {e}")

    try:
        if dp.storage:
            await dp.storage.close()
            logger.info("Storage closed")
    except Exception as e:
        logger.warning(f"Error closing storage: {e}")

    logger.info("Bot has been shut down successfully")
