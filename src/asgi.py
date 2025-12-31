"""
ASGI application factory for production deployment with Gunicorn + Uvicorn workers.

This module provides the ASGI application instance that Gunicorn can use.
"""
from fastapi import FastAPI
from contextlib import asynccontextmanager

from core import get_logger
from config import settings
from api import setup_api_routers
from core.bot import init_bot, shutdown_bot

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler for FastAPI application.
    Manages startup and shutdown events.
    """
    # Startup
    logger.info(f"Starting {settings.APP_NAME}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    logger.info(f"Initializing bot for webhook mode")

    try:
        await init_bot()
        logger.info("Bot initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize bot: {e}", exc_info=True)
        raise

    yield

    # Shutdown
    logger.info("Shutting down application...")
    try:
        await shutdown_bot()
        logger.info("Bot shutdown completed")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}", exc_info=True)


def create_app() -> FastAPI:
    """
    Application factory for creating FastAPI instance.

    Returns:
        FastAPI: Configured FastAPI application
    """
    app = FastAPI(
        title=settings.APP_NAME,
        debug=settings.DEBUG,
        lifespan=lifespan,
    )

    # Setup API routers
    setup_api_routers(app)

    logger.info("FastAPI application created")
    return app


# Create the application instance for ASGI servers (Gunicorn/Uvicorn)
app = create_app()

