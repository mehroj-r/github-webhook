from typing import Optional, List, Tuple
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


async def send_message(bot, chat_id: int, text: str, url_buttons: Optional[List[Tuple[str, str]]] = None) -> None:
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
        keyboard = []
        for button_text, url in url_buttons:
            keyboard.append([InlineKeyboardButton(text=button_text, url=url)])
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

    await bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)
