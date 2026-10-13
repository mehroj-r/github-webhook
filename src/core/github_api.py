"""Minimal GitHub REST client for the inline actions (re-run, approve, merge). Requires GH_TOKEN."""

from typing import Any

import aiohttp

from config import settings
from core import get_logger

logger = get_logger(__name__)

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=15)


class GitHubAPIError(Exception):
    """A GitHub API call failed; ``message`` is GitHub's explanation when it sent one."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(f"GitHub API {status}: {message}")
        self.status = status
        self.message = message


def is_configured() -> bool:
    return bool(settings.GH_TOKEN)


async def _request(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if not settings.GH_TOKEN:
        raise GitHubAPIError(0, "GH_TOKEN is not configured")

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {settings.GH_TOKEN}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    url = f"{settings.GH_API_URL.rstrip('/')}{path}"
    try:
        async with (
            aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session,
            session.request(method, url, json=payload, headers=headers) as response,
        ):
            try:
                body = await response.json(content_type=None)
            except ValueError:  # e.g. an HTML error page from a proxy
                body = None
            if response.status >= 400:
                message = body.get("message") if isinstance(body, dict) else None
                raise GitHubAPIError(response.status, message or response.reason or "request failed")
            return body if isinstance(body, dict) else {}
    except aiohttp.ClientError as e:
        logger.error("GitHub API %s %s failed: %s", method, path, e)
        raise GitHubAPIError(0, "GitHub is unreachable, try again later") from e


async def rerun_failed_jobs(repo: str, run_id: int) -> None:
    await _request("POST", f"/repos/{repo}/actions/runs/{run_id}/rerun-failed-jobs")


async def approve_pull_request(repo: str, number: int) -> None:
    await _request("POST", f"/repos/{repo}/pulls/{number}/reviews", {"event": "APPROVE"})


async def merge_pull_request(repo: str, number: int) -> str:
    """Merge with GH_MERGE_METHOD. Returns the merge commit SHA."""
    result = await _request("PUT", f"/repos/{repo}/pulls/{number}/merge", {"merge_method": settings.GH_MERGE_METHOD})
    return str(result.get("sha") or "")
