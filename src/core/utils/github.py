"""Utility functions for GitHub webhook handling."""

import hashlib
import hmac
import json
from html import escape
from typing import Any

from config import settings
from core import get_logger

logger = get_logger(__name__)

SIGNATURE_PREFIX = "sha256="


def verify_signature(body: bytes, signature_header: str | None, secret: str | None = None) -> bool:
    """
    Verify the GitHub webhook HMAC-SHA256 signature.

    Args:
        body: Raw request body bytes
        signature_header: Value of the X-Hub-Signature-256 header
        secret: Webhook secret (defaults to settings.GH_WEBHOOK_SECRET)

    Returns:
        bool: True if the signature is valid, False otherwise
    """
    secret = settings.GH_WEBHOOK_SECRET if secret is None else secret
    if not secret:
        logger.warning("GH_WEBHOOK_SECRET is not configured. Skipping webhook signature verification.")
        return True

    if not signature_header or not signature_header.startswith(SIGNATURE_PREFIX):
        return False

    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    received = signature_header[len(SIGNATURE_PREFIX) :]
    return hmac.compare_digest(expected, received)


async def send_unhandled_event_to_master(
    event_type: str,
    headers: dict[str, Any],
    body: dict[str, Any],
) -> bool:
    """
    Send unhandled GitHub event details to the master chat for analysis and review.

    Args:
        event_type: The GitHub event type that wasn't handled
        headers: Dictionary of request headers
        body: The request body/payload

    Returns:
        bool: True if message was sent successfully, False otherwise
    """
    if not settings.MASTER_CHAT_ID:
        logger.warning(
            "MASTER_CHAT_ID not configured. Cannot send unhandled event notification for %s",
            event_type,
        )
        return False

    try:
        from core.bot import bot
        from core.utils.bot import send_message

        # Format headers for display (filter sensitive info and format nicely)
        headers_text = "<b>Headers:</b>\n"
        important_headers = [
            "X-GitHub-Event",
            "X-GitHub-Hook-ID",
            "X-GitHub-Delivery",
            "User-Agent",
            "X-GitHub-Hook-Installation-Target-Type",
            "X-GitHub-Hook-Installation-Target-ID",
        ]

        normalized_headers = {str(key).lower(): value for key, value in headers.items()}
        for header_name in important_headers:
            value = normalized_headers.get(header_name.lower())
            if value is not None:
                headers_text += f"<code>{escape(header_name)}</code>: <code>{escape(str(value))}</code>\n"

        # Format body preview (limit size). Escape so the JSON cannot break Telegram HTML parsing.
        body_json = json.dumps(body, indent=2, default=str)
        body_preview = body_json if len(body_json) <= 2500 else body_json[:2500] + "\n... (truncated)"

        # Build the message
        message = (
            f"<b>⚠️ Unhandled GitHub Event</b>\n\n"
            f"<b>Event Type:</b> <code>{escape(event_type)}</code>\n\n"
            f"{headers_text}\n"
            f"<b>Body Preview:</b>\n"
            f"<pre>{escape(body_preview)}</pre>\n\n"
            f"<i>This event type doesn't have a handler yet. "
            f"Please analyze and add support in the next update.</i>"
        )

        # Send the message
        await send_message(bot=bot, chat_id=settings.MASTER_CHAT_ID, text=message)

        logger.info(
            "Successfully sent unhandled %s event notification to master chat",
            event_type,
        )
        return True

    except Exception as e:
        logger.error(
            "Failed to send unhandled event notification to master chat: %s",
            e,
            exc_info=True,
        )
        return False


async def send_to_master(text: str) -> bool:
    """Post an informational message to the bot owner's chat. Returns False when not configured or on failure."""
    if not settings.MASTER_CHAT_ID:
        return False
    try:
        from core.bot import bot
        from core.utils.bot import send_message

        await send_message(bot=bot, chat_id=settings.MASTER_CHAT_ID, text=text)
        return True
    except Exception as e:
        logger.error("Failed to send message to master chat: %s", e)
        return False
