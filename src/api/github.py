from fastapi import APIRouter, Request, HTTPException, status

from config import settings
from core import get_logger
from handlers.github.models.events import BaseEvent
from handlers.github.models.headers import WebhookHeaders


logger = get_logger(__name__)

router = APIRouter(prefix="/github", tags=["github"])


@router.post(path=settings.GH_WEBHOOK_PATH)
async def github_webhook(request: Request):
    """Handle incoming webhook requests from GitHub"""

    # Validate webhook headers
    try:
        headers = WebhookHeaders.model_validate(request.headers)
    except Exception as e:
        logger.error("Invalid webhook headers: %s", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook headers")

    # Get and execute handler
    event_type = headers.event_type
    handler = headers.get_event_handler()

    if not handler:
        logger.warning("No handler registered for event type: %s", event_type.value)
        return {"status": "ignored", "reason": "no_handler"}

    # Parse request body
    try:
        payload = await request.json()
    except Exception as e:
        logger.error("Failed to parse request body: %s", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload")

    # Parse payload into appropriate event model
    event_model: BaseEvent = headers.get_event_model()
    if not event_model:
        logger.error("No event model defined for event type: %s", event_type.value)
        return {"status": "error", "reason": "no_event_model"}

    try:
        event = event_model.model_validate(payload)
    except Exception as e:
        logger.error("Failed to parse %s event payload: %s", event_type.value, e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid {event_type.value} event payload")

    # Execute handler
    try:
        await handler(event=event)
        logger.info("Successfully handled %s event", event_type.value)
        return {"status": "processed", "event_type": event_type.value}
    except Exception as e:
        logger.error("Error handling %s event: %s", event_type.value, e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to process webhook")
