from fastapi import APIRouter, Request, HTTPException, status

from config import settings
from core import get_logger
from core.decorators import GitHubEventRegistry
from core.enums import GHEventType
from handlers.github.models.headers import WebhookHeaders
from handlers.github.models.events import PushEvent, CreateEvent, DeleteEvent


logger = get_logger(__name__)

router = APIRouter(prefix="/github", tags=["github"])

# Mapping of event types to their corresponding Pydantic models
EVENT_MODEL_MAP = {
    GHEventType.PUSH: PushEvent,
    GHEventType.CREATE: CreateEvent,
    GHEventType.DELETE: DeleteEvent,
}


@router.post(path=settings.GH_WEBHOOK_PATH)
async def github_webhook(request: Request):
    """Handle incoming webhook requests from GitHub"""

    # Validate webhook headers
    try:
        headers = WebhookHeaders.model_validate(request.headers)
    except Exception as e:
        logger.error("Invalid webhook headers: %s", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook headers")

    # Parse event type
    try:
        event_type = GHEventType(headers.event)
    except ValueError:
        logger.warning("Unsupported GitHub event type: %s", headers.event)
        return {"status": "ignored", "reason": "unsupported_event_type"}

    # Get and execute handler
    handler = GitHubEventRegistry.get_handler(event=event_type)

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
    event_model_class = EVENT_MODEL_MAP.get(event_type)
    if not event_model_class:
        logger.error("No event model defined for event type: %s", event_type.value)
        return {"status": "error", "reason": "no_event_model"}

    try:
        event = event_model_class.model_validate(payload)
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
