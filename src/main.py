import asyncio
import signal
import sys

from core.bot import init_bot, shutdown_bot
from core import get_logger
from config import settings

logger = get_logger(__name__)


async def main():
    """Main entry point for the bot"""
    try:
        logger.info(f"Starting {settings.APP_NAME}")
        logger.info(f"Debug mode: {settings.DEBUG}")
        logger.info(f"Webhook mode: {settings.USE_WEBHOOK}")

        await init_bot()

        # If using webhook, keep the script running
        if settings.USE_WEBHOOK:
            logger.info("Bot initialized with webhook. Waiting for incoming updates...")
            # Keep the script running indefinitely
            await asyncio.Event().wait()

    except Exception as e:
        logger.error(f"Error during bot initialization: {e}", exc_info=True)
        sys.exit(1)


def signal_handler(sig, frame):
    """Handle shutdown signals gracefully"""
    logger.info(f"Received signal {sig}. Shutting down gracefully...")
    asyncio.create_task(shutdown_bot())
    sys.exit(0)


if __name__ == "__main__":
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
