from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Telegram hard limit for a single text message
MAX_MESSAGE_LENGTH = 4096
TRUNCATION_SUFFIX = "\n\n<i>... (truncated)</i>"


def truncate_message(text: str, limit: int = MAX_MESSAGE_LENGTH) -> str:
    """Trim a message so it fits within Telegram's text length limit."""
    if len(text) <= limit:
        return text
    return text[: limit - len(TRUNCATION_SUFFIX)] + TRUNCATION_SUFFIX


async def send_message(bot, chat_id: int, text: str, url_buttons: list[tuple[str, str]] | None = None) -> None:
    """
    Send a message using the bot instance with optional URL buttons

    Args:
        bot: The bot instance
        chat_id: Chat ID to send the message to
        text: Message text (supports HTML formatting)
        url_buttons: Optional list of tuples (button_text, url) for inline keyboard buttons
    """
    reply_markup = None

    if url_buttons:
        # Create inline keyboard with URL buttons
        keyboard = [[InlineKeyboardButton(text=button_text, url=url)] for button_text, url in url_buttons]
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

    await bot.send_message(chat_id=chat_id, text=truncate_message(text), reply_markup=reply_markup)
