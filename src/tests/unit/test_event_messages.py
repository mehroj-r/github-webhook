"""Message builders for the dedicated event handlers."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from handlers.github.events import (
    check_suite,
    dependabot_alert,
    deployment_status,
    issue_comment,
    issues,
    pull_request,
    pull_request_review,
    release,
    secret_scanning_alert,
    workflow_run,
)
from handlers.github.models import events as m
from tests.payloads import REPOSITORY, USER

GH = "https://github.com/octocat/Hello-World"
PR = {
    "number": 7,
    "title": "Add <feature> & docs",
    "html_url": f"{GH}/pull/7",
    "user": {"login": "alice", "html_url": "https://github.com/alice"},
    "head": {"ref": "feature/x"},
    "base": {"ref": "main"},
    "additions": 10,
    "deletions": 2,
    "changed_files": 3,
    "draft": False,
    "merged": False,
    "labels": [{"name": "bug"}],
    "body": "First paragraph.\n\nSecond paragraph.",
}


def base(**extra):
    return {"repository": REPOSITORY, "sender": USER, **extra}


class TestPullRequest:
    @pytest.mark.unit
    def test_opened_message(self):
        event = m.PullRequestEvent.model_validate(base(action="opened", number=7, pull_request=PR))
        text = pull_request.build_message(event)
        assert "Pull request opened" in text
        assert "#7 Add &lt;feature&gt; &amp; docs" in text
        assert "<code>feature/x</code> → <code>main</code> [+10 / -2 / 3 files]" in text
        assert "<code>bug</code>" in text
        assert "<blockquote>First paragraph.</blockquote>" in text
        assert pull_request.build_buttons(event)[1] == ("📄 Files changed", f"{GH}/pull/7/files")

    @pytest.mark.unit
    def test_merged_vs_closed(self):
        merged = m.PullRequestEvent.model_validate(
            base(action="closed", number=7, pull_request={**PR, "merged": True, "merged_by": {"login": "bob"}})
        )
        closed = m.PullRequestEvent.model_validate(base(action="closed", number=7, pull_request=PR))
        assert "Pull request merged" in pull_request.build_message(merged)
        assert "Merged by bob" in pull_request.build_message(merged)
        assert "Pull request closed" in pull_request.build_message(closed)

    @pytest.mark.unit
    def test_review_requested_names_reviewer(self):
        event = m.PullRequestEvent.model_validate(
            base(action="review_requested", number=7, pull_request=PR, requested_reviewer={"login": "carol"})
        )
        assert "Reviewer: carol" in pull_request.build_message(event)

    @pytest.mark.async_
    async def test_noisy_actions_are_ignored(self):
        event = m.PullRequestEvent.model_validate(base(action="synchronize", number=7, pull_request=PR))
        with patch("handlers.github.events.pull_request.resolve_target", AsyncMock()) as resolve:
            await pull_request.handle.__wrapped__(event=event, session=AsyncMock())
        resolve.assert_not_awaited()


class TestReviewsIssuesComments:
    @pytest.mark.unit
    def test_review_states(self):
        for state, expected in (("approved", "Review approved"), ("changes_requested", "Changes requested")):
            event = m.PullRequestReviewEvent.model_validate(
                base(action="submitted", pull_request=PR, review={"state": state, "user": {"login": "d"}, "body": "ok"})
            )
            text = pull_request_review.build_message(event)
            assert expected in text
            assert "Reviewer: d" in text

    @pytest.mark.unit
    def test_issue_opened_and_closed(self):
        issue = {"number": 3, "title": "Crash", "html_url": f"{GH}/issues/3", "labels": [], "body": "It breaks"}
        opened = m.IssuesEvent.model_validate(base(action="opened", issue=issue))
        closed = m.IssuesEvent.model_validate(base(action="closed", issue={**issue, "state_reason": "completed"}))
        assert "Issue opened" in issues.build_message(opened)
        assert "<blockquote>It breaks</blockquote>" in issues.build_message(opened)
        assert "Reason: <code>completed</code>" in issues.build_message(closed)

    @pytest.mark.unit
    def test_issue_comment_on_pull_request(self):
        event = m.IssueCommentEvent.model_validate(
            base(
                action="created",
                issue={"number": 7, "title": "PR", "html_url": f"{GH}/pull/7", "pull_request": {"url": "x"}},
                comment={"body": "LGTM", "user": {"login": "e"}, "html_url": f"{GH}/pull/7#c1"},
            )
        )
        text = issue_comment.build_message(event)
        assert "New comment on pull request" in text
        assert "<blockquote>LGTM</blockquote>" in text
        assert issue_comment.build_buttons(event) == [("💬 View Comment", f"{GH}/pull/7#c1")]


class TestReleaseAndCI:
    @pytest.mark.unit
    def test_release(self):
        event = m.ReleaseEvent.model_validate(
            base(
                action="published",
                release={"tag_name": "v1.0", "name": "One", "html_url": f"{GH}/releases/v1.0", "prerelease": True, "body": "Notes"},
            )
        )
        text = release.build_message(event)
        assert "Pre-release published" in text
        assert "One</a> (<code>v1.0</code>)" in text

    @pytest.mark.unit
    def test_workflow_run_completed_with_duration(self):
        run = {
            "name": "CI",
            "run_number": 12,
            "run_attempt": 2,
            "html_url": f"{GH}/actions/runs/1",
            "head_branch": "main",
            "event": "push",
            "conclusion": "failure",
            "run_started_at": "2026-01-01T10:00:00Z",
            "updated_at": "2026-01-01T10:05:30Z",
            "actor": {"login": "f"},
        }
        event = m.WorkflowRunEvent.model_validate(base(action="completed", workflow_run=run, workflow={"name": "CI"}))
        text = workflow_run.build_message(event)
        assert "❌ Workflow failure in 5m" in text
        assert "CI #12</a> (attempt 2)" in text
        started = m.WorkflowRunEvent.model_validate(base(action="requested", workflow_run=run, workflow={"name": "CI"}))
        assert "Workflow queued" in workflow_run.build_message(started)

    @pytest.mark.unit
    def test_check_suite(self):
        suite = {"conclusion": "success", "head_branch": "main", "head_sha": "abcdef1234567", "app": {"name": "GitHub Actions"}}
        event = m.CheckSuiteEvent.model_validate(base(action="completed", check_suite=suite))
        text = check_suite.build_message(event)
        assert "✅ Check suite success" in text
        assert f"{GH}/commits/abcdef1234567/checks" in text

    @pytest.mark.unit
    def test_deployment_status(self):
        event = m.DeploymentStatusEvent.model_validate(
            base(
                deployment={"environment": "production", "ref": "main", "creator": {"login": "g"}},
                deployment_status={"state": "failure", "environment": "production", "log_url": "https://logs", "description": "boom"},
            )
        )
        text = deployment_status.build_message(event)
        assert "Deployment failed" in text
        assert "<code>production</code>" in text
        assert deployment_status.build_buttons(event) == [("📜 View Logs", "https://logs")]


class TestSecurityAlerts:
    @pytest.mark.unit
    def test_dependabot(self):
        alert = {
            "html_url": f"{GH}/security/dependabot/1",
            "security_advisory": {"summary": "Prototype pollution", "severity": "high"},
            "security_vulnerability": {"severity": "critical", "first_patched_version": {"identifier": "4.17.21"}},
            "dependency": {"package": {"name": "lodash", "ecosystem": "npm"}, "manifest_path": "package.json"},
        }
        event = m.DependabotAlertEvent.model_validate(base(action="created", alert=alert))
        text = dependabot_alert.build_message(event)
        assert "🔴 Severity: <b>critical</b>" in text
        assert "<code>lodash</code> (npm) in <code>package.json</code>" in text
        assert "Patched in <code>4.17.21</code>" in text

    @pytest.mark.unit
    def test_secret_scanning(self):
        alert = {"number": 4, "html_url": f"{GH}/security/secret-scanning/4", "secret_type_display_name": "AWS Key", "resolution": "revoked"}
        event = m.SecretScanningAlertEvent.model_validate(base(action="resolved", alert=alert))
        text = secret_scanning_alert.build_message(event)
        assert "Secret alert resolved" in text
        assert "Resolution: <code>revoked</code>" in text


class TestRegistryUsesDedicatedHandlers:
    @pytest.mark.unit
    def test_dedicated_handlers_override_generic(self):
        import handlers.github  # noqa: F401
        from core.decorators import GitHubEventRegistry
        from core.enums import GHEventType

        for event_type in (
            GHEventType.PULL_REQUEST,
            GHEventType.ISSUES,
            GHEventType.RELEASE,
            GHEventType.WORKFLOW_RUN,
            GHEventType.DEPENDABOT_ALERT,
        ):
            handler = GitHubEventRegistry.get_handler(event=event_type)
            assert handler is not None
            assert handler.__name__ == "handle", event_type
