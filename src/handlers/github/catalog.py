"""Catalog of GitHub events users can toggle per repository."""

from core.enums import GHEventType

# Events offered in the /events keyboard, in display order. Index positions are used in callback data.
NOTIFIABLE_EVENTS: list[tuple[GHEventType, str]] = [
    (GHEventType.PUSH, "Pushes"),
    (GHEventType.CREATE, "Branch/tag created"),
    (GHEventType.DELETE, "Branch/tag deleted"),
    (GHEventType.PULL_REQUEST, "Pull requests"),
    (GHEventType.PULL_REQUEST_REVIEW, "PR reviews"),
    (GHEventType.PULL_REQUEST_REVIEW_COMMENT, "PR review comments"),
    (GHEventType.ISSUES, "Issues"),
    (GHEventType.ISSUE_COMMENT, "Issue comments"),
    (GHEventType.RELEASE, "Releases"),
    (GHEventType.WORKFLOW_RUN, "Workflow runs"),
    (GHEventType.WORKFLOW_JOB, "Workflow jobs"),
    (GHEventType.CHECK_SUITE, "Check suites"),
    (GHEventType.CHECK_RUN, "Check runs"),
    (GHEventType.DEPLOYMENT_STATUS, "Deployments"),
    (GHEventType.DEPENDABOT_ALERT, "Dependabot alerts"),
    (GHEventType.SECRET_SCANNING_ALERT, "Secret scanning alerts"),
    (GHEventType.CODE_SCANNING_ALERT, "Code scanning alerts"),
    (GHEventType.STAR, "Stars"),
    (GHEventType.FORK, "Forks"),
    (GHEventType.DISCUSSION, "Discussions"),
    (GHEventType.DISCUSSION_COMMENT, "Discussion comments"),
    (GHEventType.COMMIT_COMMENT, "Commit comments"),
    (GHEventType.MEMBER, "Collaborators"),
    (GHEventType.REPOSITORY, "Repository changes"),
    (GHEventType.PING, "Pings"),
]

# Pseudo-event controlling every event type that is not listed above
OTHER_EVENTS_KEY = "other"
OTHER_EVENTS_LABEL = "Other events"

EVENT_KEYS: list[str] = [event.value for event, _ in NOTIFIABLE_EVENTS] + [OTHER_EVENTS_KEY]
EVENT_LABELS: dict[str, str] = {event.value: label for event, label in NOTIFIABLE_EVENTS} | {
    OTHER_EVENTS_KEY: OTHER_EVENTS_LABEL
}

# Enabled for a repository until its admins change it
DEFAULT_ENABLED_EVENTS: frozenset[str] = frozenset(
    {
        GHEventType.PUSH.value,
        GHEventType.CREATE.value,
        GHEventType.DELETE.value,
        GHEventType.PULL_REQUEST.value,
        GHEventType.PULL_REQUEST_REVIEW.value,
        GHEventType.ISSUES.value,
        GHEventType.ISSUE_COMMENT.value,
        GHEventType.RELEASE.value,
        GHEventType.WORKFLOW_RUN.value,
        GHEventType.DEPLOYMENT_STATUS.value,
        GHEventType.DEPENDABOT_ALERT.value,
        GHEventType.SECRET_SCANNING_ALERT.value,
        GHEventType.PING.value,
    }
)


def event_key(event_type: str) -> str:
    """Map a raw GitHub event type onto the toggle key that controls it."""
    return event_type if event_type in EVENT_LABELS else OTHER_EVENTS_KEY
