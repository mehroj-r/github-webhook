from datetime import datetime
from typing import Optional, List, Union

from pydantic import BaseModel, HttpUrl, field_validator


class User(BaseModel):
    """Model for GitHub user information"""

    login: str
    id: int
    node_id: str
    avatar_url: HttpUrl
    gravatar_id: str
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
    type: str
    user_view_type: Optional[str] = None
    site_admin: bool
    name: Optional[str] = None
    email: Optional[str] = None


class Owner(BaseModel):
    """Model for repository owner"""

    name: Optional[str] = None
    email: Optional[str] = None
    login: str
    id: int
    node_id: str
    avatar_url: HttpUrl
    gravatar_id: str
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
    type: str
    user_view_type: str
    site_admin: bool


class Repository(BaseModel):
    """Model for GitHub repository"""

    id: int
    node_id: str
    name: str
    full_name: str
    private: bool
    owner: Owner
    html_url: HttpUrl
    description: Optional[str] = None
    fork: bool
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
    git_url: str
    ssh_url: str
    clone_url: HttpUrl
    svn_url: HttpUrl
    homepage: Optional[str] = None
    size: int
    stargazers_count: int
    watchers_count: int
    language: Optional[str] = None
    has_issues: bool
    has_projects: bool
    has_downloads: bool
    has_wiki: bool
    has_pages: bool
    has_discussions: bool
    forks_count: int
    mirror_url: Optional[str] = None
    archived: bool
    disabled: bool
    open_issues_count: int
    license: Optional[str] = None
    allow_forking: bool
    is_template: bool
    web_commit_signoff_required: bool
    topics: List[str]
    visibility: str
    forks: int
    open_issues: int
    watchers: int
    default_branch: str
    stargazers: Optional[int] = None
    master_branch: Optional[str] = None

    @field_validator("created_at", "updated_at", "pushed_at", mode="before")
    @classmethod
    def parse_datetime(cls, v: Union[int, str, datetime]) -> datetime:
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
    date: datetime
    username: Optional[str] = None


class Commit(BaseModel):
    """Model for individual commit in push event"""

    id: str
    tree_id: str
    distinct: bool
    message: str
    timestamp: datetime
    url: HttpUrl
    author: CommitAuthor
    committer: CommitAuthor
    added: List[str]
    removed: List[str]
    modified: List[str]


class Pusher(BaseModel):
    """Model for the user who pushed the commits"""

    name: str
    email: str
