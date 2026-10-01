from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, HttpUrl

from handlers.github.models.shared import Commit, Hook, Pusher, Repository, User


class BaseEvent(BaseModel):
    """Base model for GitHub events"""

    model_config = ConfigDict(extra="allow")

    action: str | None = None
    repository: Repository | None = None
    sender: User | None = None


PayloadObject = dict[str, Any]
PayloadObjects = list[PayloadObject]


class PingEvent(BaseEvent):
    """
    Model for GitHub ping webhook events
    Triggered when a webhook is created or updated
    """

    zen: str
    hook_id: int
    hook: Hook
    repository: Repository | None = None
    sender: User | None = None


class PushEvent(BaseEvent):
    """
    Main model for GitHub push webhook events
    Triggered when a Git branch or tag is pushed
    """

    ref: str
    base_ref: str | None = None
    compare: HttpUrl
    commits: list[Commit]
    head_commit: Commit | None = None

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

    @property
    def ref_url(self) -> HttpUrl:
        """Get the URL to the branch or tag in the repository"""
        if self.is_tag or self.is_branch:
            return HttpUrl(f"{self.repository.html_url}/tree/{self.ref_name}")
        return self.repository.html_url


class CreateEvent(BaseEvent):
    """
    GitHub create webhook event
    Triggered when a Git branch or tag is created
    """

    ref: str
    ref_type: Literal["tag", "branch"]

    master_branch: str | None = None
    description: str | None = None

    pusher_type: str = "user"
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


class DeleteEvent(BaseEvent):
    """
    GitHub delete webhook event
    Triggered when a Git branch or tag is deleted
    """

    ref: str
    ref_type: Literal["tag", "branch"]

    pusher_type: str = "user"
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


class BranchProtectionConfigurationEvent(BaseEvent):
    action: Literal["disabled", "enabled"]


class BranchProtectionRuleEvent(BaseEvent):
    action: Literal["created", "deleted", "edited"]
    rule: PayloadObject


class CheckRunEvent(BaseEvent):
    action: Literal["completed", "created", "requested_action", "rerequested"]
    check_run: PayloadObject


class CheckSuiteEvent(BaseEvent):
    action: Literal["completed", "requested", "rerequested"]
    check_suite: PayloadObject


class CodeScanningAlertEvent(BaseEvent):
    action: Literal[
        "appeared_in_branch",
        "closed_by_user",
        "created",
        "fixed",
        "reopened",
        "reopened_by_user",
        "updated_assignment",
    ]
    alert: PayloadObject
    commit_oid: str
    ref: str


class CommitCommentEvent(BaseEvent):
    comment: PayloadObject


class CustomPropertyEvent(BaseEvent):
    action: Literal["created", "deleted", "promote_to_enterprise", "updated"]
    definition: PayloadObject


class CustomPropertyValuesEvent(BaseEvent):
    new_property_values: PayloadObjects
    old_property_values: PayloadObjects


class DependabotAlertEvent(BaseEvent):
    action: Literal[
        "assignees_changed",
        "auto_dismissed",
        "auto_reopened",
        "created",
        "dismissed",
        "fixed",
        "reintroduced",
        "reopened",
    ]
    alert: PayloadObject


class DeployKeyEvent(BaseEvent):
    action: Literal["created", "deleted"]
    key: PayloadObject


class DeploymentEvent(BaseEvent):
    deployment: PayloadObject
    workflow: PayloadObject | None = None
    workflow_run: PayloadObject | None = None


class DeploymentProtectionRuleEvent(BaseEvent):
    environment: str
    event: str
    sha: str
    ref: str
    deployment_callback_url: str
    deployment: PayloadObject | None = None
    pull_requests: PayloadObjects


class DeploymentReviewEvent(BaseEvent):
    action: Literal["approved", "rejected", "requested"]
    approver: PayloadObject | None = None
    comment: str | None = None
    reviewers: PayloadObjects | None = None
    since: str
    workflow_job_run: PayloadObject | None = None
    workflow_job_runs: PayloadObjects | None = None
    workflow_run: PayloadObject | None = None


class DeploymentStatusEvent(BaseEvent):
    check_run: PayloadObject | None = None
    deployment: PayloadObject
    deployment_status: PayloadObject
    workflow: PayloadObject | None = None
    workflow_run: PayloadObject | None = None


class DiscussionEvent(BaseEvent):
    action: Literal[
        "answered",
        "category_changed",
        "closed",
        "created",
        "deleted",
        "edited",
        "labeled",
        "locked",
        "pinned",
        "reopened",
        "transferred",
        "unanswered",
        "unlabeled",
        "unlocked",
        "unpinned",
    ]
    discussion: PayloadObject
    answer: PayloadObject | None = None


class DiscussionCommentEvent(BaseEvent):
    action: Literal["created", "deleted", "edited"]
    comment: PayloadObject
    discussion: PayloadObject


class ForkEvent(BaseEvent):
    forkee: PayloadObject


class GithubAppAuthorizationEvent(BaseEvent):
    pass


class GollumEvent(BaseEvent):
    pages: PayloadObjects


class InstallationEvent(BaseEvent):
    action: Literal["created", "deleted", "new_permissions_accepted", "suspend", "unsuspend"]
    repositories: PayloadObjects | None = None
    requester: PayloadObject | None = None


class InstallationRepositoriesEvent(BaseEvent):
    action: Literal["added", "removed"]
    repositories_added: PayloadObjects
    repositories_removed: PayloadObjects
    repository_selection: str
    requester: PayloadObject | None = None


class InstallationTargetEvent(BaseEvent):
    account: PayloadObject
    changes: PayloadObject
    target_type: str


class IssueCommentEvent(BaseEvent):
    action: Literal["created", "deleted", "edited", "pinned", "unpinned"]
    comment: PayloadObject
    issue: PayloadObject


class IssueDependenciesEvent(BaseEvent):
    action: Literal["blocked_by_added", "blocked_by_removed", "blocking_added", "blocking_removed"]
    blocked_issue_id: int
    blocked_issue: PayloadObject
    blocking_issue_id: int
    blocking_issue: PayloadObject
    blocking_issue_repo: PayloadObject


class IssuesEvent(BaseEvent):
    action: Literal[
        "assigned",
        "closed",
        "deleted",
        "demilestoned",
        "edited",
        "labeled",
        "locked",
        "milestoned",
        "opened",
        "pinned",
        "reopened",
        "transferred",
        "typed",
        "unassigned",
        "unlabeled",
        "unlocked",
        "unpinned",
        "untyped",
    ]
    assignee: PayloadObject | None = None
    issue: PayloadObject


class LabelEvent(BaseEvent):
    action: Literal["created", "deleted", "edited"]
    label: PayloadObject


class MarketplacePurchaseEvent(BaseEvent):
    action: Literal["cancelled", "changed", "pending_change", "pending_change_cancelled", "purchased"]
    effective_date: str
    marketplace_purchase: PayloadObject
    previous_marketplace_purchase: PayloadObject | None = None


class MemberEvent(BaseEvent):
    action: Literal["added", "edited", "removed"]
    changes: PayloadObject | None = None
    member: PayloadObject | None = None


class MembershipEvent(BaseEvent):
    action: Literal["added", "removed"]
    member: PayloadObject | None = None
    scope: str
    team: PayloadObject


class MergeGroupEvent(BaseEvent):
    action: Literal["checks_requested", "destroyed"]
    merge_group: PayloadObject


class MetaEvent(BaseEvent):
    hook: PayloadObject
    hook_id: int


class MilestoneEvent(BaseEvent):
    action: Literal["closed", "created", "deleted", "edited", "opened"]
    milestone: PayloadObject


class OrgBlockEvent(BaseEvent):
    action: Literal["blocked", "unblocked"]
    blocked_user: PayloadObject | None = None


class OrganizationEvent(BaseEvent):
    action: Literal["deleted", "member_added", "member_invited", "member_removed", "renamed"]
    membership: PayloadObject | None = None


class PackageEvent(BaseEvent):
    action: Literal["published", "updated"]
    package: PayloadObject


class PageBuildEvent(BaseEvent):
    build: PayloadObject
    id: int


class PersonalAccessTokenRequestEvent(BaseEvent):
    action: Literal["approved", "cancelled", "created", "denied"]
    personal_access_token_request: PayloadObject


class ProjectCardEvent(BaseEvent):
    action: Literal["converted", "created", "deleted", "edited", "moved"]
    project_card: PayloadObject
    changes: PayloadObject | None = None


class ProjectEvent(BaseEvent):
    action: Literal["closed", "created", "deleted", "edited", "reopened"]
    project: PayloadObject


class ProjectColumnEvent(BaseEvent):
    action: Literal["created", "deleted", "edited", "moved"]
    project_column: PayloadObject


class ProjectsV2Event(BaseEvent):
    action: Literal["closed", "created", "deleted", "edited", "reopened"]
    projects_v2: PayloadObject


class ProjectsV2ItemEvent(BaseEvent):
    action: Literal["archived", "converted", "created", "deleted", "edited", "reordered", "restored"]
    projects_v2_item: PayloadObject
    changes: PayloadObject | None = None


class ProjectsV2StatusUpdateEvent(BaseEvent):
    action: Literal["created", "deleted", "edited"]
    projects_v2_status_update: PayloadObject


class PublicEvent(BaseEvent):
    pass


class PullRequestEvent(BaseEvent):
    action: Literal[
        "assigned",
        "auto_merge_disabled",
        "auto_merge_enabled",
        "closed",
        "converted_to_draft",
        "demilestoned",
        "dequeued",
        "edited",
        "enqueued",
        "labeled",
        "locked",
        "milestoned",
        "opened",
        "ready_for_review",
        "reopened",
        "review_request_removed",
        "review_requested",
        "synchronize",
        "unassigned",
        "unlabeled",
        "unlocked",
    ]
    pull_request: PayloadObject
    assignee: PayloadObject | None = None
    number: int


class PullRequestReviewCommentEvent(BaseEvent):
    action: Literal["created", "deleted", "edited"]
    comment: PayloadObject
    pull_request: PayloadObject


class PullRequestReviewEvent(BaseEvent):
    action: Literal["dismissed", "edited", "submitted"]
    pull_request: PayloadObject
    review: PayloadObject


class PullRequestReviewThreadEvent(BaseEvent):
    action: Literal["resolved", "unresolved"]
    pull_request: PayloadObject
    thread: PayloadObject
    updated_at: str


class RegistryPackageEvent(BaseEvent):
    action: Literal["published", "updated"]
    registry_package: PayloadObject


class ReleaseEvent(BaseEvent):
    action: Literal["created", "deleted", "edited", "prereleased", "published", "released", "unpublished"]
    release: PayloadObject


class RepositoryEvent(BaseEvent):
    action: Literal[
        "archived",
        "created",
        "deleted",
        "edited",
        "privatized",
        "publicized",
        "renamed",
        "transferred",
        "unarchived",
    ]


class RepositoryAdvisoryEvent(BaseEvent):
    action: Literal["published", "reported"]
    repository_advisory: PayloadObject


class RepositoryDispatchEvent(BaseEvent):
    action: str
    client_payload: PayloadObject | None = None
    branch: str | None = None


class RepositoryImportEvent(BaseEvent):
    status: str


class RepositoryRulesetEvent(BaseEvent):
    action: Literal["created", "deleted", "edited"]
    repository_ruleset: PayloadObject


class RepositoryVulnerabilityAlertEvent(BaseEvent):
    action: Literal["create", "dismiss", "reopen", "resolve"]
    alert: PayloadObject


class SecretScanningAlertEvent(BaseEvent):
    action: Literal["assigned", "created", "publicly_leaked", "reopened", "resolved", "unassigned", "validated"]
    alert: PayloadObject
    assignee: PayloadObject | None = None


class SecretScanningAlertLocationEvent(BaseEvent):
    alert: PayloadObject
    location: PayloadObject


class SecretScanningScanEvent(BaseEvent):
    type: str
    source: str
    started_at: str
    completed_at: str
    secret_types: list[str]
    custom_pattern_name: str | None = None
    custom_pattern_scope: str | None = None


class SecurityAdvisoryEvent(BaseEvent):
    action: Literal["published", "updated", "withdrawn"]
    security_advisory: PayloadObject


class SecurityAndAnalysisEvent(BaseEvent):
    changes: PayloadObject


class SponsorshipEvent(BaseEvent):
    action: Literal[
        "cancelled",
        "created",
        "edited",
        "pending_cancellation",
        "pending_tier_change",
        "tier_changed",
    ]
    sponsorship: PayloadObject


class StarEvent(BaseEvent):
    action: Literal["created", "deleted"]
    starred_at: str | None = None


class StatusEvent(BaseEvent):
    commit: PayloadObject
    branches: PayloadObjects
    avatar_url: str | None = None
    context: str | None = None
    created_at: str | None = None
    description: str | None = None
    id: int | None = None
    name: str | None = None
    sha: str | None = None
    state: str | None = None
    target_url: str | None = None
    updated_at: str | None = None


class SubIssuesEvent(BaseEvent):
    action: Literal["parent_issue_added", "parent_issue_removed", "sub_issue_added", "sub_issue_removed"]
    parent_issue: PayloadObject
    parent_issue_repo: PayloadObject
    sub_issue: PayloadObject
    parent_issue_id: int
    sub_issue_id: int


class TeamAddEvent(BaseEvent):
    team: PayloadObject


class TeamEvent(BaseEvent):
    action: Literal["added_to_repository", "created", "deleted", "edited", "removed_from_repository"]
    team: PayloadObject


class WatchEvent(BaseEvent):
    action: Literal["started"]


class WorkflowDispatchEvent(BaseEvent):
    inputs: PayloadObject
    ref: str
    workflow: str


class WorkflowJobEvent(BaseEvent):
    action: Literal["completed", "in_progress", "queued", "waiting"]
    workflow_job: PayloadObject
    deployment: PayloadObject | None = None


class WorkflowRunEvent(BaseEvent):
    action: Literal["completed", "in_progress", "requested"]
    workflow_run: PayloadObject
    workflow: PayloadObject
