from html import escape

from sqlalchemy.ext.asyncio import AsyncSession

from core.decorators import GitHubEventRegistry
from core.enums import GHEventType
from core.notifications import notify, resolve_target
from handlers.github.formatting import repo_link, user_link
from handlers.github.models.events import DeploymentStatusEvent

STATE_TITLES = {
    "success": "✅ Deployment succeeded",
    "failure": "❌ Deployment failed",
    "error": "❌ Deployment errored",
    "inactive": "💤 Deployment inactive",
}


@GitHubEventRegistry.register(event=GHEventType.DEPLOYMENT_STATUS)
async def handle(event: DeploymentStatusEvent, session: AsyncSession) -> None:
    """Handle GitHub deployment_status events (final states only)"""
    state = str(event.deployment_status.get("state", "")).lower()
    if state not in STATE_TITLES or not event.repository:
        return

    target = await resolve_target(
        session,
        repo_name=event.repository.full_name,
        event_type=GHEventType.DEPLOYMENT_STATUS.value,
        branch=event.deployment.get("ref"),
    )
    if not target:
        return

    await notify(
        target,
        text=build_message(event),
        url_buttons=build_buttons(event),
        session=session,
        event_type=GHEventType.DEPLOYMENT_STATUS.value,
    )


def build_message(event: DeploymentStatusEvent) -> str:
    status = event.deployment_status
    deployment = event.deployment
    state = str(status.get("state", "")).lower()
    environment = status.get("environment") or deployment.get("environment") or "?"
    ref = deployment.get("ref") or str(deployment.get("sha", ""))[:7]

    message = (
        f"<b>{STATE_TITLES[state]}</b> in {repo_link(event)}\n"
        f"🌍 Environment: <code>{escape(str(environment))}</code> · ref <code>{escape(str(ref))}</code>\n"
        f"👤 {user_link(deployment.get('creator'))}"
    )
    if status.get("description"):
        message += f"\n📝 {escape(str(status['description'])[:200])}"
    return message


def build_buttons(event: DeploymentStatusEvent) -> list[tuple[str, str]]:
    status = event.deployment_status
    buttons = []
    if status.get("environment_url") or status.get("target_url"):
        buttons.append(("🌍 Open Environment", str(status.get("environment_url") or status.get("target_url"))))
    if status.get("log_url"):
        buttons.append(("📜 View Logs", str(status["log_url"])))
    return buttons
