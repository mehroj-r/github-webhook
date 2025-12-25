from pydantic import BaseModel

from typing import List, Optional, Literal
from pydantic import HttpUrl

from handlers.github.models.shared import User, Repository, Commit, Pusher


class PushEvent(BaseModel):
    """
    Main model for GitHub push webhook events
    Triggered when a Git branch or tag is pushed
    """

    ref: str
    base_ref: Optional[str] = None
    compare: HttpUrl
    commits: List[Commit]
    head_commit: Optional[Commit] = None

    before: str
    after: str

    repository: Repository
    pusher: Pusher
    sender: User

    created: bool
    deleted: bool
    forced: bool

    @property
    def is_tag(self) -> bool:
        """Check if this is a tag push event"""
        return self.ref.startswith("refs/tags/")

    @property
    def is_branch(self) -> bool:
        """Check if this is a branch push event"""
        return self.ref.startswith("refs/heads/")

    @property
    def ref_name(self) -> str:
        """Extract the tag or branch name from the ref"""
        if self.is_tag:
            return self.ref.replace("refs/tags/", "")
        elif self.is_branch:
            return self.ref.replace("refs/heads/", "")
        return self.ref


class CreateEvent(BaseModel):
    """
    GitHub create webhook event
    Triggered when a Git branch or tag is created
    """

    ref: str
    ref_type: Literal["tag", "branch"]

    master_branch: str
    description: str

    pusher_type: Literal["user", "deploy_key"]
    repository: Repository
    sender: User

    @property
    def is_tag(self) -> bool:
        """Check if this event created a tag"""
        return self.ref_type == "tag"

    @property
    def is_branch(self) -> bool:
        """Check if this event created a branch"""
        return self.ref_type == "branch"

    @property
    def ref_name(self) -> str:
        """Get the name of the created tag or branch"""
        return self.ref


class DeleteEvent(BaseModel):
    """
    GitHub delete webhook event
    Triggered when a Git branch or tag is deleted
    """

    ref: str
    ref_type: Literal["tag", "branch"]

    pusher_type: Literal["user", "deploy_key"]
    repository: Repository
    sender: User

    @property
    def is_tag(self) -> bool:
        """Check if this event deleted a tag"""
        return self.ref_type == "tag"

    @property
    def is_branch(self) -> bool:
        """Check if this event deleted a branch"""
        return self.ref_type == "branch"

    @property
    def ref_name(self) -> str:
        """Get the name of the deleted tag or branch"""
        return self.ref
