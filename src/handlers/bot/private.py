from aiogram import Router
from aiogram.filters import CommandStart

router = Router()


@router.message(CommandStart())
async def handle_start_command(message):
    await message.answer("Hello! Welcome to the GitHub Webhook Bot.")
