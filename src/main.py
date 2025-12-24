import asyncio
import signal
import sys
from typing import Optional

from core.bot import init_bot, shutdown_bot
from core import get_logger
from config import settings
from core.server import start_fastapi_server

logger = get_logger(__name__)

# Global variable to hold the server task
server_task: Optional[asyncio.Task] = None


async def main():
    """Main entry point for the bot"""
    global server_task

    try:
        logger.info(f"Starting {settings.APP_NAME}")
        logger.info(f"Debug mode: {settings.DEBUG}")
        logger.info(f"Webhook mode: {settings.USE_WEBHOOK}")

        # Initialize the bot
        await init_bot()

        # If webhook mode, start FastAPI server
        if settings.USE_WEBHOOK:
            logger.info("Starting in webhook mode with FastAPI server")
            await start_fastapi_server()
        else:
            logger.info("Running in polling mode (FastAPI server not started)")
            # Keep the application running in polling mode
            await asyncio.Event().wait()

    except Exception as exc:
        logger.error(f"Error during bot initialization: {exc}", exc_info=True)
        sys.exit(1)


async def shutdown():
    """Shutdown both bot and server"""
    global server_task

    logger.info("Initiating shutdown...")

    # Shutdown the bot
    await shutdown_bot()

    # Cancel server task if running
    if server_task and not server_task.done():
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass

    logger.info("Shutdown complete")


def signal_handler(sig, frame):
    """Handle shutdown signals gracefully"""
    logger.info(f"Received signal {sig}. Shutting down gracefully...")
    loop = asyncio.get_event_loop()
    loop.create_task(shutdown())


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
