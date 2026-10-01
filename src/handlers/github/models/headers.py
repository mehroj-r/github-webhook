import json

from fastapi import HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from core.enums import ContentType, GHEventType
from handlers.github.models.events import BaseEvent


class WebhookHeaders(BaseModel):
    """Model for GitHub webhook headers."""

    hook_id: str = Field(..., alias="X-GitHub-Hook-ID")
    event_type: GHEventType = Field(..., alias="X-GitHub-Event")
    delivery: str = Field(..., alias="X-GitHub-Delivery")
    signature: str | None = Field(default=None, alias="X-Hub-Signature-256")
    user_agent: str = Field(..., alias="User-Agent")
    target_type: str = Field(..., alias="X-GitHub-Hook-Installation-Target-Type")
    target_id: str = Field(..., alias="X-GitHub-Hook-Installation-Target-ID")
    content_type: ContentType = Field(..., alias="Content-Type")

    @field_validator("content_type", mode="before")
    @classmethod
    def strip_content_type_params(cls, value: str) -> str:
        """Drop media type parameters (e.g. '; charset=utf-8') before matching the enum."""
        if isinstance(value, str):
            return value.split(";", 1)[0].strip().lower()
        return value

    def get_event_model(self) -> type[BaseEvent] | None:
        """Get the corresponding event model class for the event type."""
        from core.decorators import GitHubEventRegistry

        return GitHubEventRegistry.get_event_model(event=self.event_type)

    def get_event_handler(self):
        """Get the corresponding event handler for the event type."""
        from core.decorators import GitHubEventRegistry

        return GitHubEventRegistry.get_handler(event=self.event_type)

    async def extract_payload(self, request: Request) -> dict:
        """Extract payload from the request based on content type.

        :param request: FastAPI Request object
        :return: Parsed payload as a dictionary
        :raises HTTPException: If payload extraction fails
        """
        match self.content_type:
            case ContentType.JSON:
                payload = await request.json()
            case ContentType.FORM_URLENCODED:
                form = await request.form()
                payload_str = form.get("payload")
                if not isinstance(payload_str, str) or not payload_str:
                    raise HTTPException(status_code=400, detail="Payload not found")
                payload = json.loads(payload_str)
            case _:
                raise HTTPException(status_code=400, detail="Invalid payload")

        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="Payload must be a JSON object")

        return payload
