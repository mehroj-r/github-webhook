from html import escape

from sqlalchemy.ext.asyncio import AsyncSession

from core.decorators import GitHubEventRegistry
from core.enums import GHEventType
from core.notifications import notify, resolve_target
from handlers.github.formatting import actor, repo_link
from handlers.github.models.events import SecretScanningAlertEvent

ACTION_TITLES = {
    "created": "🚨 Secret detected",
    "publicly_leaked": "🚨 Secret publicly leaked",
    "reopened": "🚨 Secret alert reopened",
    "resolved": "✅ Secret alert resolved",
    "validated": "⚠️ Secret confirmed valid",
}


@GitHubEventRegistry.register(event=GHEventType.SECRET_SCANNING_ALERT)
async def handle(event: SecretScanningAlertEvent, session: AsyncSession) -> None:
    """Handle GitHub secret_scanning_alert events"""
    if event.action not in ACTION_TITLES or not event.repository:
        return

    target = await resolve_target(
        session, repo_name=event.repository.full_name, event_type=GHEventType.SECRET_SCANNING_ALERT.value
    )
    if not target:
        return

    await notify(
        target,
        text=build_message(event),
        url_buttons=build_buttons(event),
        session=session,
        event_type=GHEventType.SECRET_SCANNING_ALERT.value,
    )


def build_message(event: SecretScanningAlertEvent) -> str:
    alert = event.alert
    secret_type = alert.get("secret_type_display_name") or alert.get("secret_type") or "secret"

    message = (
        f"<b>{ACTION_TITLES[event.action]}</b> in {repo_link(event)}\n"
        f"🔑 Type: <b>{escape(str(secret_type))}</b> · alert #{alert.get('number', '?')}\n"
        f"👤 {actor(event)}"
    )
    if event.action == "resolved" and alert.get("resolution"):
        message += f"\n📌 Resolution: <code>{escape(str(alert['resolution']))}</code>"
    if alert.get("validity") and event.action != "resolved":
        message += f"\n🧪 Validity: <code>{escape(str(alert['validity']))}</code>"
    return message


def build_buttons(event: SecretScanningAlertEvent) -> list[tuple[str, str]]:
    url = event.alert.get("html_url")
    return [("🚨 View Alert", str(url))] if url else []
