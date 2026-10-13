"""Callback handlers for the inline GitHub actions on notifications (admin-only)."""

from html import escape

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from core import get_logger, github_api
from core.github_api import GitHubAPIError
from handlers.github.actions import APPROVE, CANCEL, MERGE, MERGE_CONFIRM, PREFIX, RERUN, ActionData, pack, unpack

from .filters import ChatAdminFilter
from .settings import _repo_for_chat

logger = get_logger(__name__)

router = Router()


def _who(query: CallbackQuery) -> str:
    user = query.from_user
    return escape(f"@{user.username}" if user.username else user.full_name)


def confirm_merge_keyboard(data: ActionData) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Confirm merge", callback_data=pack(MERGE_CONFIRM, data.repo_id, data.number)
                ),
                InlineKeyboardButton(text="✖️ Cancel", callback_data=pack(CANCEL, data.repo_id, data.number)),
            ]
        ]
    )


@router.callback_query(F.data.startswith(f"{PREFIX}:"), ChatAdminFilter())
async def handle_github_action(query: CallbackQuery, session: AsyncSession) -> None:
    data = unpack(query.data or "")
    if data is None or not isinstance(query.message, Message):
        await query.answer()
        return
    message = query.message

    if data.action == CANCEL:
        await message.edit_text("✖️ Merge cancelled.")
        await query.answer()
        return

    # The button must belong to a repository connected to the chat it was pressed in
    repo = await _repo_for_chat(session, message.chat.id, data.repo_id)
    if repo is None:
        await query.answer("Repository is not connected to this chat.", show_alert=True)
        return

    if data.action == MERGE:
        await message.reply(
            f"🔀 Merge <b>#{data.number}</b> in {escape(repo.title)} using <code>{settings.GH_MERGE_METHOD}</code>?",
            reply_markup=confirm_merge_keyboard(data),
        )
        await query.answer()
        return

    if data.action not in {RERUN, APPROVE, MERGE_CONFIRM}:
        await query.answer("Unknown action.", show_alert=True)
        return

    try:
        if data.action == RERUN:
            await github_api.rerun_failed_jobs(repo.title, data.number)
            result = f"🔁 Re-run of failed jobs requested by {_who(query)}."
        elif data.action == APPROVE:
            await github_api.approve_pull_request(repo.title, data.number)
            result = f"✅ #{data.number} approved by {_who(query)}."
        else:
            sha = await github_api.merge_pull_request(repo.title, data.number)
            result = f"🎉 #{data.number} merged by {_who(query)}" + (f" (<code>{sha[:7]}</code>)." if sha else ".")
    except GitHubAPIError as e:
        logger.warning("GitHub action %s on %s#%s failed: %s", data.action, repo.title, data.number, e)
        await query.answer(f"GitHub refused: {e.message}"[:200], show_alert=True)
        return

    logger.info("GitHub action %s on %s#%s by user %s", data.action, repo.title, data.number, query.from_user.id)
    if data.action == MERGE_CONFIRM:
        await message.edit_text(result)
    else:
        await message.reply(result)
    await query.answer()
