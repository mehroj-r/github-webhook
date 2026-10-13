from typing import TYPE_CHECKING

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status

from config import settings
from core import get_logger
from core.metrics import record_delivery
from core.utils.github import send_unhandled_event_to_master, verify_signature
from database import async_session_maker
from database.enums import DeliveryStatus
from database.models import WebhookDelivery
from handlers.github.models.events import BaseEvent
from handlers.github.models.headers import WebhookHeaders

if TYPE_CHECKING:
    from handlers.github.events.base import EventHandler

logger = get_logger(__name__)

router = APIRouter(prefix="/github", tags=["github"])


async def _record_delivery(headers: WebhookHeaders) -> tuple[WebhookDelivery | None, bool]:
    """Persist the incoming delivery. Returns (row, is_new). Never blocks processing on log failures."""
    try:
        async with async_session_maker() as session:
            row, is_new = await WebhookDelivery.start(
                session,
                delivery_id=headers.delivery,
                event_type=headers.event_type.value,
                hook_id=headers.hook_id,
            )
            await session.commit()
            return row, is_new
    except Exception as e:
        logger.error("Failed to record delivery %s: %s", headers.delivery, e, exc_info=True)
        return None, True


async def _finish_delivery(
    row: WebhookDelivery | None,
    delivery_status: DeliveryStatus,
    *,
    event_type: str,
    error: str | None = None,
    action: str | None = None,
    repo_name: str | None = None,
) -> None:
    record_delivery(event_type, delivery_status.value)
    if row is None:
        return
    try:
        async with async_session_maker() as session:
            await row.finish(session, delivery_status, error=error, action=action, repo_name=repo_name)
            await session.commit()
    except Exception as e:
        logger.error("Failed to update delivery %s: %s", row.delivery_id, e, exc_info=True)


async def _run_handler(
    handler: "EventHandler",
    event: BaseEvent,
    delivery: WebhookDelivery | None,
    *,
    event_type: str,
    delivery_id: str,
    action: str | None,
    repo_name: str | None,
) -> bool:
    """Run the event handler and record the outcome. Returns True on success; never raises."""
    try:
        await handler(event=event)
    except Exception as e:
        logger.error("Error handling %s event (delivery %s): %s", event_type, delivery_id, e, exc_info=True)
        await _finish_delivery(
            delivery, DeliveryStatus.FAILED, event_type=event_type, error=repr(e), action=action, repo_name=repo_name
        )
        return False

    logger.info("Successfully handled %s event (delivery %s)", event_type, delivery_id)
    await _finish_delivery(
        delivery, DeliveryStatus.PROCESSED, event_type=event_type, action=action, repo_name=repo_name
    )
    return True


@router.post(path=settings.GH_WEBHOOK_PATH)
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
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

    # Idempotency: GitHub may redeliver the same delivery id
    delivery, is_new = await _record_delivery(headers)
    if delivery is not None and not is_new and delivery.is_processed:
        logger.info("Skipping already processed delivery %s", headers.delivery)
        record_delivery(headers.event_type.value, "duplicate")
        return {"status": "duplicate", "delivery": headers.delivery}

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
        await _finish_delivery(delivery, DeliveryStatus.IGNORED, event_type=event_type.value, error="no_handler")
        return {"status": "ignored", "reason": "no_handler", "sent_to_master": sent}

    # Parse request body
    try:
        payload = await headers.extract_payload(request)
    except HTTPException as e:
        await _finish_delivery(delivery, DeliveryStatus.FAILED, event_type=event_type.value, error=str(e.detail))
        raise
    except Exception as e:
        logger.error("Failed to parse request body: %s", e)
        await _finish_delivery(delivery, DeliveryStatus.FAILED, event_type=event_type.value, error=f"invalid body: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload") from e

    action = payload.get("action") if isinstance(payload.get("action"), str) else None
    repo_name = (
        (payload.get("repository") or {}).get("full_name") if isinstance(payload.get("repository"), dict) else None
    )

    # Parse payload into appropriate event model
    event_model: type[BaseEvent] | None = headers.get_event_model()
    if not event_model:
        logger.error("No event model defined for event type: %s", event_type.value)
        await _finish_delivery(
            delivery,
            DeliveryStatus.FAILED,
            event_type=event_type.value,
            error="no_event_model",
            action=action,
            repo_name=repo_name,
        )
        return {"status": "error", "reason": "no_event_model"}

    try:
        event = event_model.model_validate(payload)
    except Exception as e:
        logger.error("Failed to parse %s event payload (delivery %s): %s", event_type.value, headers.delivery, e)
        await _finish_delivery(
            delivery,
            DeliveryStatus.FAILED,
            event_type=event_type.value,
            error=f"validation: {e}",
            action=action,
            repo_name=repo_name,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid {event_type.value} event payload"
        ) from e

    run_kwargs = {
        "event_type": event_type.value,
        "delivery_id": headers.delivery,
        "action": action,
        "repo_name": repo_name,
    }

    # Acknowledge fast so GitHub's 10s timeout never triggers; the delivery log records the outcome
    if settings.WEBHOOK_PROCESS_IN_BACKGROUND:
        background_tasks.add_task(_run_handler, handler, event, delivery, **run_kwargs)
        return {"status": "accepted", "event_type": event_type.value}

    if await _run_handler(handler, event, delivery, **run_kwargs):
        return {"status": "processed", "event_type": event_type.value}
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to process webhook")
