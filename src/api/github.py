from fastapi import APIRouter, HTTPException, Request, status

from config import settings
from core import get_logger
from core.utils.github import send_unhandled_event_to_master, verify_signature
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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook headers") from e

    # Verify the payload signature before trusting anything in the body.
    # Starlette caches the body, so later request.json()/request.form() calls reuse it.
    body = await request.body()
    if not verify_signature(body=body, signature_header=headers.signature):
        logger.warning("Rejected GitHub delivery %s: invalid or missing signature", headers.delivery)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature")

    # Get and execute handler
    event_type = headers.event_type
    handler = headers.get_event_handler()

    if not handler:
        logger.warning("No handler registered for event type: %s", event_type.value)

        # Send unhandled event details to master chat for analysis
        try:
            payload = await headers.extract_payload(request)
        except Exception as e:
            logger.error("Failed to extract payload for unhandled event: %s", e)
            payload = {"error": "Failed to extract payload"}

        sent = await send_unhandled_event_to_master(
            event_type=event_type.value,
            headers=dict(request.headers),
            body=payload,
        )
        return {"status": "ignored", "reason": "no_handler", "sent_to_master": sent}

    # Parse request body
    try:
        payload = await headers.extract_payload(request)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to parse request body: %s", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload") from e

    # Parse payload into appropriate event model
    event_model: type[BaseEvent] | None = headers.get_event_model()
    if not event_model:
        logger.error("No event model defined for event type: %s", event_type.value)
        return {"status": "error", "reason": "no_event_model"}

    try:
        event = event_model.model_validate(payload)
    except Exception as e:
        logger.error("Failed to parse %s event payload (delivery %s): %s", event_type.value, headers.delivery, e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid {event_type.value} event payload"
        ) from e

    # Execute handler
    try:
        await handler(event=event)
        logger.info("Successfully handled %s event (delivery %s)", event_type.value, headers.delivery)
        return {"status": "processed", "event_type": event_type.value}
    except Exception as e:
        logger.error("Error handling %s event: %s", event_type.value, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to process webhook"
        ) from e
