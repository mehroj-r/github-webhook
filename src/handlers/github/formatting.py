"""Helpers for building Telegram HTML messages from GitHub payload objects."""

from html import escape
from typing import Any

from handlers.github.models.events import BaseEvent

PayloadObject = dict[str, Any]


def truncate(text: str | None, limit: int = 300) -> str:
    """Collapse a body to its first paragraph and cap its length."""
    if not text:
        return ""
    first = text.strip().split("\n\n", 1)[0].strip()
    first = " ".join(first.split())
    return first if len(first) <= limit else first[: limit - 3].rstrip() + "..."


def link(url: str | None, text: str) -> str:
    safe = escape(text)
    return f"<a href='{escape(str(url))}'>{safe}</a>" if url else safe


def user_link(user: PayloadObject | None, fallback: str = "someone") -> str:
    if not user:
        return escape(fallback)
    return link(user.get("html_url"), user.get("login") or fallback)


def actor(event: BaseEvent) -> str:
    """Sender of the event as a link."""
    if event.sender:
        return link(str(event.sender.html_url), event.sender.login)
    return "system"


def repo_link(event: BaseEvent) -> str:
    assert event.repository is not None
    return link(str(event.repository.html_url), event.repository.full_name)


def repo_url(event: BaseEvent) -> str:
    assert event.repository is not None
    return str(event.repository.html_url)


def quote(text: str | None, limit: int = 300) -> str:
    """Render a body excerpt as an indented quote block, or an empty string."""
    excerpt = truncate(text, limit)
    return f"\n<blockquote>{escape(excerpt)}</blockquote>" if excerpt else ""


def labels(items: list[PayloadObject] | None) -> str:
    names = [str(item.get("name")) for item in items or [] if item.get("name")]
    return ", ".join(f"<code>{escape(name)}</code>" for name in names)
