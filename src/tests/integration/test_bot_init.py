import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.bot import init_bot


class TestBotInitialization:
    """Test bot initialization process."""

    @pytest.mark.async_
    async def test_bot_init_with_polling_mode(self):
        """Test bot initialization with polling mode."""
        with (
            patch("core.bot.settings") as mock_settings,
            patch("core.bot._init_with_polling", new_callable=AsyncMock) as mock_polling,
            patch("core.bot.setup_bot_handlers"),
        ):
            mock_settings.USE_WEBHOOK = False
            await init_bot()
            mock_polling.assert_called_once()

    @pytest.mark.async_
    async def test_bot_init_with_webhook_mode(self):
        """Test bot initialization with webhook mode."""
        with (
            patch("core.bot.settings") as mock_settings,
            patch("core.bot._init_with_webhook", new_callable=AsyncMock) as mock_webhook,
            patch("core.bot.setup_bot_handlers"),
        ):
            mock_settings.USE_WEBHOOK = True
            await init_bot()
            mock_webhook.assert_called_once()

    @pytest.mark.async_
    async def test_bot_initialization_calls_setup(self):
        """Test that bot initialization sets up handlers."""
        with (
            patch("core.bot.settings") as mock_settings,
            patch("core.bot._init_with_polling", new_callable=AsyncMock),
            patch("core.bot.setup_bot_handlers") as mock_setup,
        ):
            mock_settings.USE_WEBHOOK = False
            await init_bot()
            mock_setup.assert_called_once()
