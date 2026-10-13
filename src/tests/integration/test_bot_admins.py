import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database.models import BotAdmin
from handlers.bot.admins import handle_admin_add, handle_admin_remove, handle_admins, parse_target
from handlers.bot.filters.admin import is_bot_admin, is_chat_admin

OWNER = 42


def make_message(text: str, reply_from: MagicMock | None = None) -> MagicMock:
    message = MagicMock()
    message.text = text
    message.from_user.id = OWNER
    message.answer = AsyncMock()
    if reply_from is None:
        message.reply_to_message = None
    else:
        message.reply_to_message.from_user = reply_from
    return message


def user(user_id: int, name: str = "Ada Lovelace", is_bot: bool = False) -> MagicMock:
    sender = MagicMock()
    sender.id = user_id
    sender.full_name = name
    sender.is_bot = is_bot
    return sender


def answer(message: MagicMock) -> str:
    return message.answer.await_args.args[0]


@pytest.fixture(autouse=True)
def owner():
    with patch("handlers.bot.admins.settings") as admins_settings, patch(
        "handlers.bot.filters.admin.settings"
    ) as filter_settings:
        admins_settings.MASTER_CHAT_ID = OWNER
        filter_settings.MASTER_CHAT_ID = OWNER
        yield


class TestParseTarget:
    @pytest.mark.unit
    @pytest.mark.parametrize(
        "text,expected",
        [("/admin_add 7", (7, None)), ("/admin_add 7 Ada L", (7, "Ada L")), ("/admin_add abc", (None, None))],
    )
    def test_arguments(self, text, expected):
        assert parse_target(make_message(text)) == expected

    @pytest.mark.unit
    def test_reply_to_user(self):
        assert parse_target(make_message("/admin_add", reply_from=user(7))) == (7, "Ada Lovelace")

    @pytest.mark.unit
    def test_reply_to_bot_is_ignored(self):
        assert parse_target(make_message("/admin_add", reply_from=user(7, is_bot=True))) == (None, None)


class TestAdminCommands:
    @pytest.mark.integration
    async def test_add_list_remove(self, sqlite_session_maker):
        async with sqlite_session_maker() as session:
            await handle_admin_add(make_message("/admin_add 7 Ada"), session=session)
            await session.commit()

        async with sqlite_session_maker() as session:
            stored = await BotAdmin.get(session, user_id=7)
            listing = make_message("/admins")
            await handle_admins(listing, session=session)

        assert stored is not None
        assert stored.name == "Ada"
        assert stored.added_by_user_id == OWNER
        assert "<code>7</code> — Ada" in answer(listing)
        assert f"<code>{OWNER}</code> — owner" in answer(listing)

        async with sqlite_session_maker() as session:
            removal = make_message("/admin_remove 7")
            await handle_admin_remove(removal, session=session)
            await session.commit()

        async with sqlite_session_maker() as session:
            assert await BotAdmin.get(session, user_id=7) is None
        assert "no longer" in answer(removal)

    @pytest.mark.integration
    async def test_add_twice_and_owner(self, sqlite_session_maker):
        async with sqlite_session_maker() as session:
            await handle_admin_add(make_message("/admin_add 7"), session=session)
            again = make_message("/admin_add 7")
            await handle_admin_add(again, session=session)
            self_add = make_message(f"/admin_add {OWNER}")
            await handle_admin_add(self_add, session=session)

        assert "already a bot admin" in answer(again)
        assert "owner already" in answer(self_add)

    @pytest.mark.integration
    async def test_remove_unknown_and_usage(self, sqlite_session_maker):
        async with sqlite_session_maker() as session:
            unknown = make_message("/admin_remove 8")
            await handle_admin_remove(unknown, session=session)
            usage = make_message("/admin_add")
            await handle_admin_add(usage, session=session)

        assert "is not a bot admin" in answer(unknown)
        assert "Usage" in answer(usage)


class TestBotAdminAccess:
    @pytest.mark.integration
    async def test_bot_admin_can_manage_any_group(self, sqlite_session_maker):
        async with sqlite_session_maker() as session:
            await BotAdmin.create(session, user_id=7)
            await session.commit()

        bot = MagicMock()
        bot.get_chat_member = AsyncMock()
        with patch("handlers.bot.filters.admin.async_session_maker", sqlite_session_maker):
            assert await is_bot_admin(7) is True
            assert await is_chat_admin(bot, chat_id=-1, chat_type="supergroup", user_id=7, sender_chat_id=None)
            assert await is_bot_admin(8) is False
        bot.get_chat_member.assert_not_called()
