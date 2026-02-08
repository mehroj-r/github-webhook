import sys
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.enums import ContentType, GHEventType


class TestGHEventType:
    """Test GHEventType enum."""

    @pytest.mark.unit
    def test_gh_event_type_values(self):
        """Test GHEventType enum values."""
        assert GHEventType.PING.value == "ping"
        assert GHEventType.PUSH.value == "push"
        assert GHEventType.CREATE.value == "create"
        assert GHEventType.DELETE.value == "delete"

    @pytest.mark.unit
    def test_gh_event_type_members(self):
        """Test GHEventType enum has expected members."""
        members = list(GHEventType)
        assert len(members) >= 4
        assert any(member.name == "PING" for member in members)
        assert any(member.name == "PUSH" for member in members)

    @pytest.mark.unit
    def test_gh_event_type_is_string_enum(self):
        """Test that GHEventType values are strings."""
        for member in GHEventType:
            assert isinstance(member.value, str)


class TestContentType:
    """Test ContentType enum."""

    @pytest.mark.unit
    def test_content_type_values(self):
        """Test ContentType enum values."""
        assert ContentType.JSON.value == "application/json"
        assert ContentType.FORM_URLENCODED.value == "application/x-www-form-urlencoded"

    @pytest.mark.unit
    def test_content_type_members(self):
        """Test ContentType enum has expected members."""
        members = list(ContentType)
        assert len(members) >= 2

    @pytest.mark.unit
    def test_content_type_is_string_enum(self):
        """Test that ContentType values are strings."""
        for member in ContentType:
            assert isinstance(member.value, str)
