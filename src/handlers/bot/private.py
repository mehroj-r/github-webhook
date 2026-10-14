from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from .texts import HELP_TEXT

router = Router()


@router.message(CommandStart())
async def handle_start_command(message: Message) -> None:
    await message.answer(HELP_TEXT)
