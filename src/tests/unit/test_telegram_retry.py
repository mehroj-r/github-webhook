import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from aiogram.exceptions import TelegramBadRequest, TelegramNetworkError, TelegramRetryAfter

from core.utils.bot import send_message, with_retry


def retry_after(seconds: int) -> TelegramRetryAfter:
    return TelegramRetryAfter(method=MagicMock(), message="Too Many Requests", retry_after=seconds)


class TestWithRetry:
    @pytest.mark.async_
    async def test_sleeps_and_retries_on_flood_control(self):
        operation = AsyncMock(side_effect=[retry_after(2), "ok"])
        with patch("core.utils.bot.asyncio.sleep", AsyncMock()) as sleep:
            assert await with_retry(operation) == "ok"
        sleep.assert_awaited_once_with(2)
        assert operation.await_count == 2

    @pytest.mark.async_
    async def test_gives_up_on_long_flood_wait(self):
        operation = AsyncMock(side_effect=retry_after(600))
        with patch("core.utils.bot.asyncio.sleep", AsyncMock()) as sleep, pytest.raises(TelegramRetryAfter):
            await with_retry(operation)
        sleep.assert_not_awaited()

    @pytest.mark.async_
    async def test_network_errors_back_off_then_raise(self):
        error = TelegramNetworkError(method=MagicMock(), message="timeout")
        operation = AsyncMock(side_effect=[error, error, error, error])
        with patch("core.utils.bot.asyncio.sleep", AsyncMock()) as sleep, pytest.raises(TelegramNetworkError):
            await with_retry(operation)
        assert operation.await_count == 4
        assert [call.args[0] for call in sleep.await_args_list] == [1, 3, 7]

    @pytest.mark.async_
    async def test_other_api_errors_are_not_retried(self):
        operation = AsyncMock(side_effect=TelegramBadRequest(method=MagicMock(), message="chat not found"))
        with pytest.raises(TelegramBadRequest):
            await with_retry(operation)
        assert operation.await_count == 1


class TestSendMessage:
    @pytest.mark.async_
    async def test_send_message_retries(self):
        bot = MagicMock()
        bot.send_message = AsyncMock(side_effect=[retry_after(1), "sent"])
        with patch("core.utils.bot.asyncio.sleep", AsyncMock()):
            assert await send_message(bot, chat_id=1, text="hi") == "sent"
        assert bot.send_message.await_count == 2
