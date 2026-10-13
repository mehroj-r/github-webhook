import asyncio
from collections.abc import Awaitable, Callable

from aiogram.exceptions import TelegramNetworkError, TelegramRetryAfter
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from core import get_logger
from core.metrics import observe_telegram_call

logger = get_logger(__name__)

# Telegram hard limit for a single text message
MAX_MESSAGE_LENGTH = 4096
TRUNCATION_SUFFIX = "\n\n<i>... (truncated)</i>"

# A button whose "url" starts with this prefix is sent as a callback button with the rest as callback data
CALLBACK_PREFIX = "callback:"
MAX_CALLBACK_DATA = 64  # bytes, Telegram limit

# Retry policy for Telegram API calls
MAX_ATTEMPTS = 4
MAX_RETRY_AFTER = 60  # seconds; longer flood waits are given up on
NETWORK_BACKOFF = (1, 3, 7)


async def with_retry[T](operation: Callable[[], Awaitable[T]], description: str = "telegram call") -> T:
    """
    Run a Telegram API call, honouring flood-control waits and retrying transient network errors.

    TelegramRetryAfter: sleep for the requested time (bounded) and retry.
    TelegramNetworkError: exponential-ish backoff. Other API errors are raised immediately.
    The first word of ``description`` is the method label of the latency metric.
    """
    with observe_telegram_call(description.split(" ", 1)[0]):
        return await _retry_loop(operation, description)


async def _retry_loop[T](operation: Callable[[], Awaitable[T]], description: str) -> T:
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return await operation()
        except TelegramRetryAfter as e:
            if attempt == MAX_ATTEMPTS or e.retry_after > MAX_RETRY_AFTER:
                raise
            logger.warning("%s rate limited; retrying in %ss (attempt %s)", description, e.retry_after, attempt)
            await asyncio.sleep(e.retry_after)
        except TelegramNetworkError as e:
            if attempt == MAX_ATTEMPTS:
                raise
            delay = NETWORK_BACKOFF[min(attempt, len(NETWORK_BACKOFF)) - 1]
            logger.warning(
                "%s failed with network error %s; retrying in %ss (attempt %s)", description, e, delay, attempt
            )
            await asyncio.sleep(delay)
    raise RuntimeError("unreachable")  # pragma: no cover


def truncate_message(text: str, limit: int = MAX_MESSAGE_LENGTH) -> str:
    """Trim a message so it fits within Telegram's text length limit."""
    if len(text) <= limit:
        return text
    return text[: limit - len(TRUNCATION_SUFFIX)] + TRUNCATION_SUFFIX


async def send_message(
    bot,
    chat_id: int,
    text: str,
    url_buttons: list[tuple[str, str]] | None = None,
    message_thread_id: int | None = None,
) -> Message:
    """
    Send a message using the bot instance with optional URL buttons

    Args:
        bot: The bot instance
        chat_id: Chat ID to send the message to
        text: Message text (supports HTML formatting)
        url_buttons: Optional list of tuples (button_text, url) for inline keyboard buttons
        message_thread_id: Forum topic to post into (supergroups with topics enabled)
    """
    return await with_retry(
        lambda: bot.send_message(
            chat_id=chat_id,
            text=truncate_message(text),
            reply_markup=build_url_keyboard(url_buttons),
            message_thread_id=message_thread_id,
        ),
        description=f"send_message to {chat_id}",
    )


def callback_button(text: str, data: str) -> tuple[str, str] | None:
    """A (text, target) button entry that triggers a callback query; None if `data` is too long."""
    if len(data.encode()) > MAX_CALLBACK_DATA:
        return None
    return text, f"{CALLBACK_PREFIX}{data}"


def is_callback_button(button: tuple[str, str]) -> bool:
    return button[1].startswith(CALLBACK_PREFIX)


def first_url(buttons: list[tuple[str, str]] | None) -> str | None:
    return next((target for _, target in buttons or [] if not target.startswith(CALLBACK_PREFIX)), None)


def build_url_keyboard(url_buttons: list[tuple[str, str]] | None) -> InlineKeyboardMarkup | None:
    """
    Inline keyboard with one URL button per row, or None when there are no buttons.
    Callback buttons (see `callback_button`) share a single row at the bottom.
    """
    if not url_buttons:
        return None
    keyboard = [
        [InlineKeyboardButton(text=text, url=target)]
        for text, target in url_buttons
        if not target.startswith(CALLBACK_PREFIX)
    ]
    actions = [
        InlineKeyboardButton(text=text, callback_data=target.removeprefix(CALLBACK_PREFIX))
        for text, target in url_buttons
        if target.startswith(CALLBACK_PREFIX)
    ]
    if actions:
        keyboard.append(actions)
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


async def edit_message(bot, chat_id: int, message_id: int, text: str, url_buttons: list[tuple[str, str]] | None = None):
    """Replace the text and buttons of a message the bot sent earlier."""
    return await with_retry(
        lambda: bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=truncate_message(text),
            reply_markup=build_url_keyboard(url_buttons),
        ),
        description=f"edit_message in {chat_id}",
    )
