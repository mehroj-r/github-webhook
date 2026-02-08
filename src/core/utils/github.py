"""Utility functions for GitHub webhook handling."""

import json
from typing import Dict, Any

from config import settings
from core import get_logger

logger = get_logger(__name__)


async def send_unhandled_event_to_master(
    event_type: str,
    headers: Dict[str, Any],
    body: Dict[str, Any],
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

        for header_name in important_headers:
            if header_name in headers:
                headers_text += f"<code>{header_name}</code>: <code>{headers[header_name]}</code>\n"

        # Format body preview (limit size)
        body_json = json.dumps(body, indent=2)
        if len(body_json) > 3000:
            body_preview = body_json[:3000] + "\n... (truncated)"
        else:
            body_preview = body_json

        # Build the message
        message = (
            f"<b>⚠️ Unhandled GitHub Event</b>\n\n"
            f"<b>Event Type:</b> <code>{event_type}</code>\n\n"
            f"{headers_text}\n"
            f"<b>Body Preview:</b>\n"
            f"<pre>{body_preview}</pre>\n\n"
            f"<i>This event type doesn't have a handler yet. "
            f"Please analyze and add support in the next update.</i>"
        )

        # Send the message
        await bot.send_message(
            chat_id=settings.MASTER_CHAT_ID,
            text=message,
            parse_mode="HTML",
        )

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
