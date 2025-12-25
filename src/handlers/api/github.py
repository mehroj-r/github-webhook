from pprint import pprint

from fastapi import APIRouter, Request

from config import settings
from handlers.api.models.github.events import PushEvent, CreateEvent
from handlers.api.models.github.headers import WebhookHeaders

router = APIRouter(prefix="/github", tags=["github"])


@router.post(path=settings.GH_WEBHOOK_PATH)
async def github_webhook(request: Request):
    """Handle incoming webhook requests from GitHub"""

    payload = await request.body()

    request_headers = request.headers
    request_body = payload.decode()

    # Parse GitHub webhook headers
    headers = WebhookHeaders.model_validate(request_headers)

    # Extract event type
    action = headers.event

    event = None
    match action:
        case "push":
            pprint("Received a push event")
            event = PushEvent.model_validate_json(request_body)
        case "create":
            pprint("Received a create event")
            event = CreateEvent.model_validate_json(request_body)
        case _:
            pprint(f"Received an unsupported event type: {action}")

    pprint(headers.model_dump())
    pprint("\n\n")
    pprint(request_body)
    pprint(event.model_dump() if event else "No event data")

    return {"status": "received"}
