from html import escape

from sqlalchemy.ext.asyncio import AsyncSession

from core import get_logger
from core.bot import bot
from core.decorators import GitHubEventRegistry
from core.enums import GHEventType
from core.utils.bot import send_message
from database.models import Chat
from handlers.github.models import events as event_models

logger = get_logger(__name__)


def _event_title(event_type: GHEventType) -> str:
    return event_type.value.replace("_", " ").title()


def _extract_details(event: event_models.BaseEvent) -> list[str]:
    ignored_fields = {"repository", "sender", "action"}
    details: list[str] = []

    for field_name in event.__class__.model_fields:
        if field_name in ignored_fields:
            continue

        value = getattr(event, field_name, None)
        if value in (None, "", [], {}):
            continue

        label = field_name.replace("_", " ").title()

        if isinstance(value, dict):
            details.append(f"• {label}: <code>object</code>")
        elif isinstance(value, list):
            details.append(f"• {label}: <code>{len(value)} item(s)</code>")
        else:
            value_text = escape(str(value))
            if len(value_text) > 120:
                value_text = f"{value_text[:117]}..."
            details.append(f"• {label}: <code>{value_text}</code>")

        if len(details) >= 3:
            break

    return details


async def _get_chat_id(repo_name: str, session: AsyncSession) -> int | None:
    chat = await Chat.get_by_repo(session, repo_name)

    if not chat:
        logger.info("No chat configured for repository %s", repo_name)
        return None

    return chat.chat_id


async def _notify(event_type: GHEventType, event: event_models.BaseEvent, session: AsyncSession) -> None:
    if not event.repository:
        logger.info("Skipping %s event without repository context", event_type.value)
        return

    chat_id = await _get_chat_id(repo_name=event.repository.full_name, session=session)
    if not chat_id:
        return

    action_text = event.action or "triggered"
    actor = event.sender.login if event.sender else "system"
    title = _event_title(event_type=event_type)

    details = _extract_details(event=event)
    details_text = "\n".join(details)
    details_block = f"\n\n{details_text}" if details_text else ""

    message = (
        f"📣 <b>{escape(title)} Event</b>\n"
        f"📦 Repository: <a href='{event.repository.html_url}'>{escape(event.repository.full_name)}</a>\n"
        f"🏷 Action: <code>{escape(action_text)}</code>\n"
    )

    if event.sender:
        message += f"👤 Actor: <a href='{event.sender.html_url}'>{escape(actor)}</a>"
    else:
        message += f"👤 Actor: <code>{actor}</code>"

    message += details_block

    await send_message(
        bot=bot,
        chat_id=chat_id,
        text=message,
        url_buttons=[("📂 View Repository", str(event.repository.html_url))],
    )


EVENT_MODEL_MAP: dict[GHEventType, type[event_models.BaseEvent]] = {
    GHEventType.BRANCH_PROTECTION_CONFIGURATION: event_models.BranchProtectionConfigurationEvent,
    GHEventType.BRANCH_PROTECTION_RULE: event_models.BranchProtectionRuleEvent,
    GHEventType.CHECK_RUN: event_models.CheckRunEvent,
    GHEventType.CHECK_SUITE: event_models.CheckSuiteEvent,
    GHEventType.CODE_SCANNING_ALERT: event_models.CodeScanningAlertEvent,
    GHEventType.COMMIT_COMMENT: event_models.CommitCommentEvent,
    GHEventType.CUSTOM_PROPERTY: event_models.CustomPropertyEvent,
    GHEventType.CUSTOM_PROPERTY_VALUES: event_models.CustomPropertyValuesEvent,
    GHEventType.DEPENDABOT_ALERT: event_models.DependabotAlertEvent,
    GHEventType.DEPLOY_KEY: event_models.DeployKeyEvent,
    GHEventType.DEPLOYMENT: event_models.DeploymentEvent,
    GHEventType.DEPLOYMENT_PROTECTION_RULE: event_models.DeploymentProtectionRuleEvent,
    GHEventType.DEPLOYMENT_REVIEW: event_models.DeploymentReviewEvent,
    GHEventType.DEPLOYMENT_STATUS: event_models.DeploymentStatusEvent,
    GHEventType.DISCUSSION: event_models.DiscussionEvent,
    GHEventType.DISCUSSION_COMMENT: event_models.DiscussionCommentEvent,
    GHEventType.FORK: event_models.ForkEvent,
    GHEventType.GITHUB_APP_AUTHORIZATION: event_models.GithubAppAuthorizationEvent,
    GHEventType.GOLLUM: event_models.GollumEvent,
    GHEventType.INSTALLATION: event_models.InstallationEvent,
    GHEventType.INSTALLATION_REPOSITORIES: event_models.InstallationRepositoriesEvent,
    GHEventType.INSTALLATION_TARGET: event_models.InstallationTargetEvent,
    GHEventType.ISSUE_COMMENT: event_models.IssueCommentEvent,
    GHEventType.ISSUE_DEPENDENCIES: event_models.IssueDependenciesEvent,
    GHEventType.ISSUES: event_models.IssuesEvent,
    GHEventType.LABEL: event_models.LabelEvent,
    GHEventType.MARKETPLACE_PURCHASE: event_models.MarketplacePurchaseEvent,
    GHEventType.MEMBER: event_models.MemberEvent,
    GHEventType.MEMBERSHIP: event_models.MembershipEvent,
    GHEventType.MERGE_GROUP: event_models.MergeGroupEvent,
    GHEventType.META: event_models.MetaEvent,
    GHEventType.MILESTONE: event_models.MilestoneEvent,
    GHEventType.ORG_BLOCK: event_models.OrgBlockEvent,
    GHEventType.ORGANIZATION: event_models.OrganizationEvent,
    GHEventType.PACKAGE: event_models.PackageEvent,
    GHEventType.PAGE_BUILD: event_models.PageBuildEvent,
    GHEventType.PERSONAL_ACCESS_TOKEN_REQUEST: event_models.PersonalAccessTokenRequestEvent,
    GHEventType.PROJECT_CARD: event_models.ProjectCardEvent,
    GHEventType.PROJECT: event_models.ProjectEvent,
    GHEventType.PROJECT_COLUMN: event_models.ProjectColumnEvent,
    GHEventType.PROJECTS_V2: event_models.ProjectsV2Event,
    GHEventType.PROJECTS_V2_ITEM: event_models.ProjectsV2ItemEvent,
    GHEventType.PROJECTS_V2_STATUS_UPDATE: event_models.ProjectsV2StatusUpdateEvent,
    GHEventType.PUBLIC: event_models.PublicEvent,
    GHEventType.PULL_REQUEST: event_models.PullRequestEvent,
    GHEventType.PULL_REQUEST_REVIEW_COMMENT: event_models.PullRequestReviewCommentEvent,
    GHEventType.PULL_REQUEST_REVIEW: event_models.PullRequestReviewEvent,
    GHEventType.PULL_REQUEST_REVIEW_THREAD: event_models.PullRequestReviewThreadEvent,
    GHEventType.REGISTRY_PACKAGE: event_models.RegistryPackageEvent,
    GHEventType.RELEASE: event_models.ReleaseEvent,
    GHEventType.REPOSITORY: event_models.RepositoryEvent,
    GHEventType.REPOSITORY_ADVISORY: event_models.RepositoryAdvisoryEvent,
    GHEventType.REPOSITORY_DISPATCH: event_models.RepositoryDispatchEvent,
    GHEventType.REPOSITORY_IMPORT: event_models.RepositoryImportEvent,
    GHEventType.REPOSITORY_RULESET: event_models.RepositoryRulesetEvent,
    GHEventType.REPOSITORY_VULNERABILITY_ALERT: event_models.RepositoryVulnerabilityAlertEvent,
    GHEventType.SECRET_SCANNING_ALERT: event_models.SecretScanningAlertEvent,
    GHEventType.SECRET_SCANNING_ALERT_LOCATION: event_models.SecretScanningAlertLocationEvent,
    GHEventType.SECRET_SCANNING_SCAN: event_models.SecretScanningScanEvent,
    GHEventType.SECURITY_ADVISORY: event_models.SecurityAdvisoryEvent,
    GHEventType.SECURITY_AND_ANALYSIS: event_models.SecurityAndAnalysisEvent,
    GHEventType.SPONSORSHIP: event_models.SponsorshipEvent,
    GHEventType.STAR: event_models.StarEvent,
    GHEventType.STATUS: event_models.StatusEvent,
    GHEventType.SUB_ISSUES: event_models.SubIssuesEvent,
    GHEventType.TEAM_ADD: event_models.TeamAddEvent,
    GHEventType.TEAM: event_models.TeamEvent,
    GHEventType.WATCH: event_models.WatchEvent,
    GHEventType.WORKFLOW_DISPATCH: event_models.WorkflowDispatchEvent,
    GHEventType.WORKFLOW_JOB: event_models.WorkflowJobEvent,
    GHEventType.WORKFLOW_RUN: event_models.WorkflowRunEvent,
}


def _register_handler(event_type: GHEventType, model_cls: type[event_models.BaseEvent]) -> None:
    async def handler(event: event_models.BaseEvent, session: AsyncSession) -> None:
        await _notify(event_type=event_type, event=event, session=session)

    # The registry reads the `event` annotation to pick the payload model for this event type
    handler.__annotations__["event"] = model_cls
    handler.__name__ = f"handle_{event_type.value}"
    GitHubEventRegistry.register(event=event_type)(handler)


def register_generic_handlers() -> None:
    """Register a generic notification handler for every event without a dedicated handler."""
    for event_type, model_cls in EVENT_MODEL_MAP.items():
        if GitHubEventRegistry.get_handler(event=event_type) is None:
            _register_handler(event_type=event_type, model_cls=model_cls)
