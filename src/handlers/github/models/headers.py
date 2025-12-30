from typing import Optional, Callable

from pydantic import BaseModel, Field

from core.enums import GHEventType
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

    def get_event_model(self) -> Optional[BaseEvent]:
        """Get the corresponding event model class for the event type."""
        from core.decorators import GitHubEventRegistry

        return GitHubEventRegistry.get_event_model(event=self.event_type)

    def get_event_handler(self)  -> Optional[Callable[[BaseEvent], None]]:
        """Get the corresponding event handler for the event type."""
        from core.decorators import GitHubEventRegistry

        return GitHubEventRegistry.get_handler(event=self.event_type)
