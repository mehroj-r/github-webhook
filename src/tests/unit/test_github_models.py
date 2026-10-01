import sys
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from handlers.github.models.events import CreateEvent, PingEvent, PushEvent
from tests.payloads import COMMIT, REPOSITORY, USER, push_payload  # noqa: F401

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
