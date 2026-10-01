from html import escape

from sqlalchemy.ext.asyncio import AsyncSession

from core.decorators import GitHubEventRegistry
from core.enums import GHEventType
from core.notifications import notify, resolve_target
from handlers.github.formatting import repo_link
from handlers.github.models.events import DependabotAlertEvent

ACTION_TITLES = {
    "created": "🛡 New Dependabot alert",
    "reopened": "🛡 Dependabot alert reopened",
    "reintroduced": "🛡 Vulnerability reintroduced",
    "fixed": "✅ Dependabot alert fixed",
    "dismissed": "🙈 Dependabot alert dismissed",
    "auto_dismissed": "🙈 Dependabot alert auto-dismissed",
}
SEVERITY_ICONS = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}


@GitHubEventRegistry.register(event=GHEventType.DEPENDABOT_ALERT)
async def handle(event: DependabotAlertEvent, session: AsyncSession) -> None:
    """Handle GitHub dependabot_alert events"""
    if event.action not in ACTION_TITLES or not event.repository:
        return

    target = await resolve_target(
        session, repo_name=event.repository.full_name, event_type=GHEventType.DEPENDABOT_ALERT.value
    )
    if not target:
        return

    await notify(target, text=build_message(event), url_buttons=build_buttons(event))


def build_message(event: DependabotAlertEvent) -> str:
    alert = event.alert
    advisory = alert.get("security_advisory") or {}
    vulnerability = alert.get("security_vulnerability") or {}
    dependency = alert.get("dependency") or {}
    package = dependency.get("package") or {}
    severity = str(vulnerability.get("severity") or advisory.get("severity") or "unknown").lower()

    message = (
        f"<b>{ACTION_TITLES[event.action]}</b> in {repo_link(event)}\n"
        f"{SEVERITY_ICONS.get(severity, '⚪')} Severity: <b>{escape(severity)}</b>\n"
        f"📦 <code>{escape(str(package.get('name', '?')))}</code> ({escape(str(package.get('ecosystem', '?')))})"
    )
    if dependency.get("manifest_path"):
        message += f" in <code>{escape(str(dependency['manifest_path']))}</code>"
    if advisory.get("summary"):
        message += f"\n📝 {escape(str(advisory['summary'])[:200])}"
    if vulnerability.get("first_patched_version"):
        patched = (vulnerability["first_patched_version"] or {}).get("identifier")
        if patched:
            message += f"\n🩹 Patched in <code>{escape(str(patched))}</code>"
    return message


def build_buttons(event: DependabotAlertEvent) -> list[tuple[str, str]]:
    url = event.alert.get("html_url")
    return [("🛡 View Alert", str(url))] if url else []
