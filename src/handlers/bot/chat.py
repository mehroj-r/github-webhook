from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from core.decorators import parse_command
from database.models import Chat, GithubRepository
from database.enums import ChatType
from .validators.chat import ConnectRepoCommandValidator

router = Router()


@router.message(Command("connect_repo"))
@parse_command(arguments=["repo_url"], validator=ConnectRepoCommandValidator())
async def handle_connect_repo(message: Message, repo_url: str, session: AsyncSession) -> None:

    msg = await message.answer("🔗 Connecting chat to repository...")

    # Create chat instance if not exists
    chat, _ = await Chat.get_or_create(
        session=session,
        chat_id=message.chat.id,
        defaults={
            "chat_type": ChatType(message.chat.type),
            "title": message.chat.title or message.chat.full_name,
        },
    )

    # Create repository connection if not exists
    repo, created = await GithubRepository.get_or_create(
        session=session,
        chat_id=chat.id,
        url=repo_url,
    )

    if not created:
        await msg.edit_text("ℹ️ This chat is already connected to the specified repository.")
    else:
        await msg.edit_text("✅ Repository connected successfully.")


@router.message(F.new_chat_members)
async def handle_bot_added(message: Message):
    for member in message.new_chat_members:
        if member.is_bot and member.id == message.bot.id:
            await message.answer("👋 Hello! Thanks for adding me to this chat.")
