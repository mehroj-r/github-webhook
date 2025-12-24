from fastapi import FastAPI

from core import get_logger
from config import settings
from handlers import setup_api_routers

logger = get_logger(__name__)


async def start_fastapi_server():
    """Start the FastAPI server with uvicorn"""
    import uvicorn
    from core.logger import get_logger_config

    logger_config = get_logger_config()
    logger.info(f"Starting FastAPI server on {settings.HOST}:{settings.PORT}")

    app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG)
    setup_api_routers(app)

    config = uvicorn.Config(
        app,
        host=settings.HOST,
        port=settings.PORT,
        log_level="info" if settings.DEBUG else "warning",
        log_config=logger_config,
    )
    server = uvicorn.Server(config)
    await server.serve()
