from datetime import datetime
from html import escape

from sqlalchemy.ext.asyncio import AsyncSession

from core.decorators import GitHubEventRegistry
from core.enums import GHEventType
from core.notifications import notify, resolve_target
from core.utils.duration import format_duration
from handlers.github.formatting import repo_link, user_link
from handlers.github.models.events import WorkflowRunEvent

CONCLUSION_ICONS = {
    "success": "✅",
    "failure": "❌",
    "cancelled": "🚫",
    "timed_out": "⏰",
    "action_required": "⚠️",
    "neutral": "⚪",
    "skipped": "⏭",
    "stale": "🕸",
}


@GitHubEventRegistry.register(event=GHEventType.WORKFLOW_RUN)
async def handle(event: WorkflowRunEvent, session: AsyncSession) -> None:
    """Handle GitHub workflow_run events (start and completion of a workflow)"""
    if event.action not in {"requested", "completed"} or not event.repository:
        return

    target = await resolve_target(
        session,
        repo_name=event.repository.full_name,
        event_type=GHEventType.WORKFLOW_RUN.value,
        branch=event.workflow_run.get("head_branch"),
    )
    if not target:
        return

    await notify(target, text=build_message(event), url_buttons=build_buttons(event))


def _duration(run: dict) -> str:
    started, updated = run.get("run_started_at"), run.get("updated_at")
    if not started or not updated:
        return ""
    try:
        delta = datetime.fromisoformat(str(updated).replace("Z", "+00:00")) - datetime.fromisoformat(
            str(started).replace("Z", "+00:00")
        )
    except ValueError:
        return ""
    return f" in {format_duration(delta)}" if delta.total_seconds() > 0 else ""


def build_message(event: WorkflowRunEvent) -> str:
    run = event.workflow_run
    name = run.get("name") or (event.workflow or {}).get("name") or "Workflow"
    number = run.get("run_number")
    attempt = run.get("run_attempt") or 1
    attempt_text = f" (attempt {attempt})" if attempt > 1 else ""

    if event.action == "completed":
        conclusion = str(run.get("conclusion") or "unknown")
        icon = CONCLUSION_ICONS.get(conclusion, "ℹ️")
        title = f"{icon} Workflow {conclusion.replace('_', ' ')}{_duration(run)}"
    else:
        title = "🏃 Workflow started"

    return (
        f"<b>{title}</b> in {repo_link(event)}\n"
        f"⚙️ <a href='{escape(str(run.get('html_url')))}'>{escape(str(name))} #{number}</a>{attempt_text}\n"
        f"🌿 <code>{escape(str(run.get('head_branch', '?')))}</code> · trigger: <code>{escape(str(run.get('event', '?')))}</code>\n"
        f"👤 {user_link(run.get('actor') or run.get('triggering_actor'))}"
    )


def build_buttons(event: WorkflowRunEvent) -> list[tuple[str, str]]:
    url = event.workflow_run.get("html_url")
    return [("⚙️ View Run", str(url))] if url else []
