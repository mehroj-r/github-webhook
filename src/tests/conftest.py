import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    from config import settings

    mock = MagicMock(spec=settings)
    mock.BOT_TOKEN = "test-token"
    mock.USE_WEBHOOK = False
    mock.WEBHOOK_URL = "http://localhost:8000"
    mock.WEBHOOK_SECRET = "test-secret"
    mock.DATABASE_URL = "sqlite:///test.db"
    mock.DEBUG = True
    mock.LOG_DIR = "logs"
    return mock


@pytest.fixture
def mock_bot():
    """Create a mock Telegram bot."""
    bot = AsyncMock()
    bot.session = AsyncMock()
    return bot


@pytest.fixture
def mock_dispatcher():
    """Create a mock Telegram dispatcher."""
    from aiogram import Dispatcher

    dp = MagicMock(spec=Dispatcher)
    dp.feed_update = AsyncMock()
    return dp


@pytest.fixture
def async_client():
    """Create an async HTTP client for testing."""
    from httpx import AsyncClient

    return AsyncClient()
