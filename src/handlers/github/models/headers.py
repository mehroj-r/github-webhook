from typing import Optional, Callable

from pydantic import BaseModel, Field
from fastapi import Request, HTTPException

from core.enums import GHEventType, ContentType
from handlers.github.models.events import BaseEvent


class WebhookHeaders(BaseModel):
    """Model for GitHub webhook headers."""

    hook_id: str = Field(..., alias="X-GitHub-Hook-ID")
    event_type: GHEventType = Field(..., alias="X-GitHub-Event")
    delivery: str = Field(..., alias="X-GitHub-Delivery")
    signature: str = Field(default=None, alias="X-Hub-Signature-256")
    user_agent: str = Field(..., alias="User-Agent")
    target_type: str = Field(..., alias="X-GitHub-Hook-Installation-Target-Type")
    target_id: str = Field(..., alias="X-GitHub-Hook-Installation-Target-ID")
    content_type: ContentType = Field(..., alias="Content-Type")

    def get_event_model(self) -> Optional[BaseEvent]:
        """Get the corresponding event model class for the event type."""
        from core.decorators import GitHubEventRegistry

        return GitHubEventRegistry.get_event_model(event=self.event_type)

    def get_event_handler(self) -> Optional[Callable[[BaseEvent], None]]:
        """Get the corresponding event handler for the event type."""
        from core.decorators import GitHubEventRegistry

        return GitHubEventRegistry.get_handler(event=self.event_type)

    async def extract_payload(self, request: Request) -> dict:
        """Extract payload from the request based on content type.

        :param request: FastAPI Request object
        :return: Parsed payload as a dictionary
        :raises HTTPException: If payload extraction fails
        """
        import json

        match self.content_type:
            case ContentType.JSON:
                return await request.json()
            case ContentType.FORM_URLENCODED:
                form = await request.form()
                payload_str = form.get("payload")
                if payload_str:
                    return json.loads(payload_str)
            case _:
                raise HTTPException(status_code=400, detail="Invalid payload")

        raise HTTPException(status_code=400, detail="Payload not found")
