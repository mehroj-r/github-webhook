from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

router = Router()


@router.message(CommandStart())
async def handle_start_command(message: Message) -> None:
    await message.answer("Hello! Welcome to the GitHub Webhook Bot.")
