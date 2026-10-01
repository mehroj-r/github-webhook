import sys
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from handlers.github.models.events import CreateEvent, PingEvent, PushEvent

USER = {
    "login": "octocat",
    "id": 1,
    "node_id": "MDQ6VXNlcjE=",
    "avatar_url": "https://github.com/images/error/octocat_happy.gif",
    "gravatar_id": "",
    "url": "https://api.github.com/users/octocat",
    "html_url": "https://github.com/octocat",
    "followers_url": "https://api.github.com/users/octocat/followers",
    "following_url": "https://api.github.com/users/octocat/following{/other_user}",
    "gists_url": "https://api.github.com/users/octocat/gists{/gist_id}",
    "starred_url": "https://api.github.com/users/octocat/starred{/owner}{/repo}",
    "subscriptions_url": "https://api.github.com/users/octocat/subscriptions",
    "organizations_url": "https://api.github.com/users/octocat/orgs",
    "repos_url": "https://api.github.com/users/octocat/repos",
    "events_url": "https://api.github.com/users/octocat/events{/privacy}",
    "received_events_url": "https://api.github.com/users/octocat/received_events",
    "type": "User",
    "site_admin": False,
}

API = "https://api.github.com/repos/octocat/Hello-World"
REPOSITORY = {
    "id": 1296269,
    "node_id": "MDEwOlJlcG9zaXRvcnkxMjk2MjY5",
    "name": "Hello-World",
    "full_name": "octocat/Hello-World",
    "owner": USER,
    "private": False,
    "html_url": "https://github.com/octocat/Hello-World",
    "description": None,
    "fork": False,
    "url": API,
    "forks_url": f"{API}/forks",
    "keys_url": f"{API}/keys{{/key_id}}",
    "collaborators_url": f"{API}/collaborators{{/collaborator}}",
    "teams_url": f"{API}/teams",
    "hooks_url": f"{API}/hooks",
    "issue_events_url": f"{API}/issues/events{{/number}}",
    "events_url": f"{API}/events",
    "assignees_url": f"{API}/assignees{{/user}}",
    "branches_url": f"{API}/branches{{/branch}}",
    "tags_url": f"{API}/tags",
    "blobs_url": f"{API}/git/blobs{{/sha}}",
    "git_tags_url": f"{API}/git/tags{{/sha}}",
    "git_refs_url": f"{API}/git/refs{{/sha}}",
    "trees_url": f"{API}/git/trees{{/sha}}",
    "statuses_url": f"{API}/statuses/{{sha}}",
    "languages_url": f"{API}/languages",
    "stargazers_url": f"{API}/stargazers",
    "contributors_url": f"{API}/contributors",
    "subscribers_url": f"{API}/subscribers",
    "subscription_url": f"{API}/subscription",
    "commits_url": f"{API}/commits{{/sha}}",
    "git_commits_url": f"{API}/git/commits{{/sha}}",
    "comments_url": f"{API}/comments{{/number}}",
    "issue_comment_url": f"{API}/issues/comments{{/number}}",
    "contents_url": f"{API}/contents/{{+path}}",
    "compare_url": f"{API}/compare/{{base}}...{{head}}",
    "merges_url": f"{API}/merges",
    "archive_url": f"{API}/{{archive_format}}{{/ref}}",
    "downloads_url": f"{API}/downloads",
    "issues_url": f"{API}/issues{{/number}}",
    "pulls_url": f"{API}/pulls{{/number}}",
    "milestones_url": f"{API}/milestones{{/number}}",
    "notifications_url": f"{API}/notifications{{?since,all,participating}}",
    "labels_url": f"{API}/labels{{/name}}",
    "releases_url": f"{API}/releases{{/id}}",
    "deployments_url": f"{API}/deployments",
    "created_at": 1557933565,
    "updated_at": "2019-05-15T15:20:41Z",
    "pushed_at": 1557933657,
    "git_url": "git://github.com/octocat/Hello-World.git",
    "ssh_url": "git@github.com:octocat/Hello-World.git",
    "clone_url": "https://github.com/octocat/Hello-World.git",
    "svn_url": "https://github.com/octocat/Hello-World",
    "homepage": None,
    "size": 0,
    "stargazers_count": 0,
    "watchers_count": 0,
    "language": None,
    "has_issues": True,
    "has_projects": True,
    "has_downloads": True,
    "has_wiki": True,
    "has_pages": True,
    "forks_count": 0,
    "mirror_url": None,
    "archived": False,
    "disabled": False,
    "open_issues_count": 0,
    # Real payloads send the license as an object, not a string
    "license": {
        "key": "mit",
        "name": "MIT License",
        "spdx_id": "MIT",
        "url": "https://api.github.com/licenses/mit",
        "node_id": "MDc6TGljZW5zZTEz",
    },
    "forks": 0,
    "open_issues": 0,
    "watchers": 0,
    "default_branch": "main",
    "is_template": False,
    "web_commit_signoff_required": False,
    "topics": [],
    "visibility": "public",
    "custom_properties": {},
}

COMMIT = {
    "id": "6113728f27ae82c7b1a177c8d03f9e96e0adf246",
    "tree_id": "31b122c26a97cf9af023e9ddab94a82c6e77b0ea",
    "distinct": True,
    "message": "Fix <bug> & ship",
    "timestamp": "2019-05-15T15:20:41Z",
    "url": "https://github.com/octocat/Hello-World/commit/6113728f27ae82c7b1a177c8d03f9e96e0adf246",
    # Webhook commit authors carry no `date` and may have a null email
    "author": {"name": "Octocat", "email": None, "username": "octocat"},
    "committer": {"name": "GitHub", "email": "noreply@github.com"},
    "added": ["a.py"],
    "removed": [],
    "modified": ["b.py"],
}


def push_payload(**overrides) -> dict:
    payload = {
        "ref": "refs/heads/main",
        "before": "0000000000000000000000000000000000000000",
        "after": COMMIT["id"],
        "created": False,
        "deleted": False,
        "forced": False,
        "base_ref": None,
        "compare": "https://github.com/octocat/Hello-World/compare/000000000000...6113728f27ae",
        "commits": [COMMIT],
        "head_commit": COMMIT,
        "repository": REPOSITORY,
        "pusher": {"name": "octocat", "email": None},
        "sender": USER,
    }
    payload.update(overrides)
    return payload


class TestPushEvent:
    @pytest.mark.unit
    def test_push_with_license_object_and_dateless_author(self):
        event = PushEvent.model_validate(push_payload())
        assert event.ref_name == "main"
        assert event.is_branch
        assert event.commits[0].author.date is None
        assert event.repository.license["key"] == "mit"

    @pytest.mark.unit
    def test_push_repository_timestamps_are_timezone_aware(self):
        event = PushEvent.model_validate(push_payload())
        assert event.repository.pushed_at.tzinfo is not None
        assert event.repository.updated_at.tzinfo is not None

    @pytest.mark.unit
    def test_push_tag_ref(self):
        event = PushEvent.model_validate(push_payload(ref="refs/tags/v1.0.0"))
        assert event.is_tag
        assert event.ref_name == "v1.0.0"
        assert str(event.ref_url) == "https://github.com/octocat/Hello-World/tree/v1.0.0"

    @pytest.mark.async_
    async def test_push_message_escapes_html(self):
        from handlers.github.events.push import _build_commit_message

        message = await _build_commit_message(event=PushEvent.model_validate(push_payload()))
        assert "Fix &lt;bug&gt; &amp; ship" in message
        assert "<bug>" not in message


class TestCreateEvent:
    @pytest.mark.unit
    def test_create_with_null_description(self):
        event = CreateEvent.model_validate(
            {
                "ref": "feature/x",
                "ref_type": "branch",
                "master_branch": "main",
                "description": None,
                "pusher_type": "user",
                "repository": REPOSITORY,
                "sender": USER,
            }
        )
        assert event.is_branch
        assert event.description is None


class TestPingEvent:
    @pytest.mark.unit
    def test_ping_without_repository(self):
        """Organization-level hooks ping without a repository object."""
        event = PingEvent.model_validate(
            {
                "zen": "Keep it logically awesome.",
                "hook_id": 1,
                "hook": {
                    "type": "Organization",
                    "id": 1,
                    "name": "web",
                    "active": True,
                    "events": ["push"],
                    "config": {"content_type": "json", "insecure_ssl": "0", "url": "https://example.com/hook"},
                    "updated_at": "2019-05-15T15:20:41Z",
                    "created_at": "2019-05-15T15:20:41Z",
                    "url": "https://api.github.com/orgs/octo/hooks/1",
                    "ping_url": "https://api.github.com/orgs/octo/hooks/1/pings",
                    "deliveries_url": "https://api.github.com/orgs/octo/hooks/1/deliveries",
                },
                "sender": USER,
            }
        )
        assert event.repository is None
