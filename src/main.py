import asyncio
import signal
import sys

from config import settings
from core import get_logger
from core.bot import init_bot, shutdown_bot
from core.digest import start_scheduler, stop_scheduler
from core.server import start_fastapi_server
from database import close_db

logger = get_logger(__name__)


async def main() -> None:
    """Main entry point for the application"""
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    # Register signal handlers for graceful shutdown
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _request_shutdown, sig, stop_event)

    logger.info("Starting %s", settings.APP_NAME)
    logger.info("Debug mode: %s", settings.DEBUG)
    logger.info("Webhook mode: %s", settings.USE_WEBHOOK)

    try:
        await init_bot()
        start_scheduler()

        if settings.USE_WEBHOOK:
            logger.info("Starting in webhook mode with FastAPI server")
            server_task = asyncio.create_task(start_fastapi_server(), name="fastapi-server")
            stop_task = asyncio.create_task(stop_event.wait(), name="stop-signal")
            done, _ = await asyncio.wait({server_task, stop_task}, return_when=asyncio.FIRST_COMPLETED)

            if server_task in done:
                # Surface server errors; a clean exit simply falls through to shutdown
                server_task.result()
            else:
                server_task.cancel()
                await asyncio.gather(server_task, return_exceptions=True)
            stop_task.cancel()
        else:
            logger.info("Running in polling mode (FastAPI server not started)")
            await stop_event.wait()
    finally:
        await shutdown()


def _request_shutdown(sig: signal.Signals, stop_event: asyncio.Event) -> None:
    """Signal handler: ask the main loop to stop."""
    logger.info("Received signal %s. Shutting down gracefully...", sig.name)
    stop_event.set()


async def shutdown() -> None:
    """Shutdown the bot and release database connections"""
    logger.info("Initiating shutdown...")
    await stop_scheduler()
    await shutdown_bot()
    await close_db()
    logger.info("Shutdown complete")


def run() -> None:
    """Console-script entry point."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error("Fatal error: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    run()
