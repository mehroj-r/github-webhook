from pydantic import BaseModel, Field


class WebhookHeaders(BaseModel):
    """Model for GitHub webhook headers."""

    hook_id: str = Field(..., alias="X-GitHub-Hook-ID")
    event: str = Field(..., alias="X-GitHub-Event")
    delivery: str = Field(..., alias="X-GitHub-Delivery")
    signature: str = Field(default=None, alias="X-Hub-Signature-256")
    user_agent: str = Field(..., alias="User-Agent")
    target_type: str = Field(..., alias="X-GitHub-Hook-Installation-Target-Type")
    target_id: str = Field(..., alias="X-GitHub-Hook-Installation-Target-ID")
