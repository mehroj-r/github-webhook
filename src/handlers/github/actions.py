"""Inline action buttons attached to notifications. Callback data: ``gh:<action>:<repo uuid hex>:<number>``."""

from dataclasses import dataclass
from uuid import UUID

from core import github_api
from core.utils.bot import callback_button
from database.models import GithubRepository

PREFIX = "gh"
RERUN = "rerun"
APPROVE = "approve"
MERGE = "merge"  # asks for confirmation
MERGE_CONFIRM = "mergeok"
CANCEL = "cancel"

RERUN_CONCLUSIONS = {"failure", "timed_out"}
PR_ACTIONS = {"opened", "reopened", "ready_for_review"}


@dataclass(frozen=True, slots=True)
class ActionData:
    action: str
    repo_id: UUID
    number: int


def pack(action: str, repo_id: UUID, number: int) -> str:
    return f"{PREFIX}:{action}:{repo_id.hex}:{number}"


def unpack(data: str) -> ActionData | None:
    parts = data.split(":")
    if len(parts) != 4 or parts[0] != PREFIX:
        return None
    try:
        return ActionData(action=parts[1], repo_id=UUID(hex=parts[2]), number=int(parts[3]))
    except ValueError:
        return None


def _buttons(*entries: tuple[str, str, UUID, int]) -> list[tuple[str, str]]:
    if not github_api.is_configured():
        return []
    built = (callback_button(text, pack(action, repo_id, number)) for text, action, repo_id, number in entries)
    return [b for b in built if b is not None]


def workflow_run_buttons(repo: GithubRepository, action: str | None, run: dict) -> list[tuple[str, str]]:
    """Re-run button for a failed or timed-out run."""
    if action != "completed" or run.get("conclusion") not in RERUN_CONCLUSIONS or not run.get("id"):
        return []
    return _buttons(("🔁 Re-run failed jobs", RERUN, repo.id, int(run["id"])))


def pull_request_buttons(repo: GithubRepository, action: str | None, pr: dict) -> list[tuple[str, str]]:
    """Approve / merge buttons for an open, non-draft pull request."""
    if action not in PR_ACTIONS or pr.get("state") != "open" or pr.get("draft") or not pr.get("number"):
        return []
    number = int(pr["number"])
    return _buttons(("✅ Approve", APPROVE, repo.id, number), ("🔀 Merge", MERGE, repo.id, number))
