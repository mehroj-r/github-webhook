"""Inline keyboards for repository settings."""

from uuid import UUID

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from database.models import GithubRepository
from handlers.github.catalog import EVENT_KEYS, EVENT_LABELS

EVENTS_PREFIX = "ev"
REPO_PICK_PREFIX = "evr"
CLOSE_ACTION = "close"


def events_callback(repo_id: UUID, action: str | int) -> str:
    return f"{EVENTS_PREFIX}:{repo_id.hex}:{action}"


def repo_pick_callback(repo_id: UUID) -> str:
    return f"{REPO_PICK_PREFIX}:{repo_id.hex}"


def events_keyboard(repo: GithubRepository) -> InlineKeyboardMarkup:
    """Two-column toggle keyboard for the repository's event subscriptions."""
    enabled = repo.enabled_event_keys
    buttons = [
        InlineKeyboardButton(
            text=f"{'✅' if key in enabled else '▫️'} {EVENT_LABELS[key]}",
            callback_data=events_callback(repo.id, index),
        )
        for index, key in enumerate(EVENT_KEYS)
    ]
    rows = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
    rows.append([InlineKeyboardButton(text="✖ Close", callback_data=events_callback(repo.id, CLOSE_ACTION))])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def repo_picker_keyboard(repos: list[GithubRepository]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=repo.title, callback_data=repo_pick_callback(repo.id))]
        for repo in sorted(repos, key=lambda r: r.title.lower())
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
