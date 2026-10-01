import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from aiogram.types import CallbackQuery, Message

from handlers.bot.filters.admin import ADMIN_ONLY_TEXT, ChatAdminFilter, is_chat_admin


def make_bot(status: str = "member") -> MagicMock:
    bot = MagicMock()
    member = MagicMock()
    member.status = status
    bot.get_chat_member = AsyncMock(return_value=member)
    return bot


class TestIsChatAdmin:
    @pytest.mark.async_
    async def test_private_chat_always_allowed(self):
        bot = make_bot()
        assert await is_chat_admin(bot, chat_id=1, chat_type="private", user_id=1, sender_chat_id=None) is True
        bot.get_chat_member.assert_not_called()

    @pytest.mark.async_
    @pytest.mark.parametrize("status,expected", [("creator", True), ("administrator", True), ("member", False)])
    async def test_group_requires_admin_status(self, status, expected):
        bot = make_bot(status)
        result = await is_chat_admin(bot, chat_id=-1, chat_type="supergroup", user_id=7, sender_chat_id=None)
        assert result is expected
        bot.get_chat_member.assert_awaited_once_with(chat_id=-1, user_id=7)

    @pytest.mark.async_
    async def test_anonymous_admin_allowed(self):
        bot = make_bot("member")
        assert await is_chat_admin(bot, chat_id=-1, chat_type="supergroup", user_id=None, sender_chat_id=-1) is True

    @pytest.mark.async_
    async def test_bot_owner_allowed(self):
        bot = make_bot("member")
        with patch("handlers.bot.filters.admin.settings") as mock_settings:
            mock_settings.MASTER_CHAT_ID = 42
            assert await is_chat_admin(bot, chat_id=-1, chat_type="group", user_id=42, sender_chat_id=None) is True

    @pytest.mark.async_
    async def test_api_error_denies(self):
        bot = make_bot()
        bot.get_chat_member = AsyncMock(side_effect=RuntimeError("telegram down"))
        assert await is_chat_admin(bot, chat_id=-1, chat_type="group", user_id=7, sender_chat_id=None) is False


class TestChatAdminFilter:
    @staticmethod
    def message(chat_type: str = "supergroup") -> MagicMock:
        message = MagicMock(spec=Message)
        message.chat = MagicMock()
        message.chat.id = -1
        message.chat.type = chat_type
        message.from_user = MagicMock()
        message.from_user.id = 7
        message.sender_chat = None
        message.reply = AsyncMock()
        return message

    @pytest.mark.async_
    async def test_non_admin_message_gets_reply(self):
        message = self.message()
        with patch("handlers.bot.filters.admin.settings") as mock_settings:
            mock_settings.MASTER_CHAT_ID = None
            assert await ChatAdminFilter()(message, bot=make_bot("member")) is False
        message.reply.assert_awaited_once_with(ADMIN_ONLY_TEXT)

    @pytest.mark.async_
    async def test_admin_message_passes(self):
        message = self.message()
        assert await ChatAdminFilter()(message, bot=make_bot("administrator")) is True
        message.reply.assert_not_called()

    @pytest.mark.async_
    async def test_callback_query_non_admin_gets_alert(self):
        query = MagicMock(spec=CallbackQuery)
        query.message = self.message()
        query.from_user = MagicMock()
        query.from_user.id = 7
        query.answer = AsyncMock()
        with patch("handlers.bot.filters.admin.settings") as mock_settings:
            mock_settings.MASTER_CHAT_ID = None
            assert await ChatAdminFilter()(query, bot=make_bot("member")) is False
        query.answer.assert_awaited_once_with(ADMIN_ONLY_TEXT, show_alert=True)
