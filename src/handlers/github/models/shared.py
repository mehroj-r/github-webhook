from datetime import datetime

from pydantic import BaseModel, HttpUrl, field_validator


class User(BaseModel):
    """Model for GitHub user information"""

    id: int
    login: str
    name: str | None = None
    email: str | None = None
    avatar_url: HttpUrl
    type: str
    user_view_type: str | None = None

    node_id: str
    gravatar_id: str
    site_admin: bool

    url: HttpUrl
    html_url: HttpUrl
    followers_url: HttpUrl
    following_url: str
    gists_url: str
    starred_url: str
    subscriptions_url: HttpUrl
    organizations_url: HttpUrl
    repos_url: HttpUrl
    events_url: str
    received_events_url: HttpUrl


class Repository(BaseModel):
    """Model for GitHub repository"""

    id: int
    name: str
    description: str | None = None
    full_name: str
    owner: User

    private: bool
    fork: bool
    language: str | None = None
    size: int
    visibility: str
    archived: bool
    disabled: bool

    forks: int
    open_issues: int
    watchers: int
    stargazers_count: int
    watchers_count: int
    forks_count: int
    open_issues_count: int

    has_issues: bool
    has_projects: bool
    has_downloads: bool
    has_wiki: bool
    has_pages: bool
    has_discussions: bool
    allow_forking: bool
    is_template: bool
    web_commit_signoff_required: bool

    node_id: str
    homepage: str | None = None
    license: str | None = None
    topics: list[str]
    default_branch: str
    stargazers: int | None = None
    master_branch: str | None = None

    mirror_url: str | None = None
    html_url: HttpUrl
    git_url: str
    ssh_url: str
    clone_url: HttpUrl
    svn_url: HttpUrl
    url: HttpUrl
    forks_url: HttpUrl
    keys_url: str
    collaborators_url: str
    teams_url: HttpUrl
    hooks_url: HttpUrl
    issue_events_url: str
    events_url: HttpUrl
    assignees_url: str
    branches_url: str
    tags_url: HttpUrl
    blobs_url: str
    git_tags_url: str
    git_refs_url: str
    trees_url: str
    statuses_url: str
    languages_url: HttpUrl
    stargazers_url: HttpUrl
    contributors_url: HttpUrl
    subscribers_url: HttpUrl
    subscription_url: HttpUrl
    commits_url: str
    git_commits_url: str
    comments_url: str
    issue_comment_url: str
    contents_url: str
    compare_url: str
    merges_url: HttpUrl
    archive_url: str
    downloads_url: HttpUrl
    issues_url: str
    pulls_url: str
    milestones_url: str
    notifications_url: str
    labels_url: str
    releases_url: str
    deployments_url: HttpUrl

    created_at: datetime
    updated_at: datetime
    pushed_at: datetime

    @field_validator("created_at", "updated_at", "pushed_at", mode="before")
    @classmethod
    def parse_datetime(cls, v: int | str | datetime) -> datetime:
        """
        Parse datetime from multiple formats:
        - Unix timestamp (int) - from push events
        - ISO string - from create events
        - datetime object - passthrough
        """
        if isinstance(v, datetime):
            return v
        elif isinstance(v, int):
            # Unix timestamp (push event)
            return datetime.fromtimestamp(v)
        elif isinstance(v, str):
            # ISO format string (create event)
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        else:
            raise ValueError(f"Unable to parse datetime from {type(v)}: {v}")


class CommitAuthor(BaseModel):
    """Model for commit author/committer information"""

    name: str
    email: str
    username: str | None = None

    date: datetime


class Commit(BaseModel):
    """Model for individual commit in push event"""

    id: str
    url: HttpUrl
    author: CommitAuthor
    committer: CommitAuthor

    tree_id: str
    distinct: bool
    message: str

    added: list[str]
    removed: list[str]
    modified: list[str]

    timestamp: datetime


class Pusher(BaseModel):
    """Model for the user who pushed the commits"""

    name: str
    email: str


class LastResponse(BaseModel):
    code: int | None
    status: str | None
    message: str | None


class HookConfig(BaseModel):
    content_type: str
    insecure_ssl: str
    url: str


class Hook(BaseModel):
    type: str
    id: int
    name: str
    active: bool
    events: list[str]
    config: HookConfig
    updated_at: datetime
    created_at: datetime
    url: str
    test_url: str
    ping_url: str
    deliveries_url: str
    last_response: LastResponse
