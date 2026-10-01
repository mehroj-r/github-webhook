from html import escape

from sqlalchemy.ext.asyncio import AsyncSession

from core.decorators import GitHubEventRegistry
from core.enums import GHEventType
from core.notifications import notify, resolve_target
from handlers.github.events.workflow_run import CONCLUSION_ICONS
from handlers.github.formatting import repo_link, repo_url
from handlers.github.models.events import CheckSuiteEvent


@GitHubEventRegistry.register(event=GHEventType.CHECK_SUITE)
async def handle(event: CheckSuiteEvent, session: AsyncSession) -> None:
    """Handle GitHub check_suite events (completed suites only)"""
    if event.action != "completed" or not event.repository:
        return

    target = await resolve_target(
        session,
        repo_name=event.repository.full_name,
        event_type=GHEventType.CHECK_SUITE.value,
        branch=event.check_suite.get("head_branch"),
    )
    if not target:
        return

    await notify(
        target,
        text=build_message(event),
        url_buttons=build_buttons(event),
        session=session,
        event_type=GHEventType.CHECK_SUITE.value,
    )


def checks_url(event: CheckSuiteEvent) -> str:
    sha = event.check_suite.get("head_sha", "")
    return f"{repo_url(event)}/commits/{sha}/checks"


def build_message(event: CheckSuiteEvent) -> str:
    suite = event.check_suite
    conclusion = str(suite.get("conclusion") or "unknown")
    icon = CONCLUSION_ICONS.get(conclusion, "ℹ️")
    app = (suite.get("app") or {}).get("name") or "Checks"
    sha = str(suite.get("head_sha", ""))[:7]

    return (
        f"<b>{icon} Check suite {conclusion.replace('_', ' ')}</b> in {repo_link(event)}\n"
        f"🧪 {escape(str(app))} on <code>{escape(str(suite.get('head_branch', '?')))}</code> "
        f"(<a href='{escape(checks_url(event))}'>{escape(sha)}</a>)"
    )


def build_buttons(event: CheckSuiteEvent) -> list[tuple[str, str]]:
    return [("🧪 View Checks", checks_url(event))]
