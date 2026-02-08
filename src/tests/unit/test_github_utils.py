import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.utils.github import send_unhandled_event_to_master


class TestGitHubUtils:
    """Test GitHub utility functions."""

    @pytest.mark.async_
    async def test_send_unhandled_event_without_master_chat_id(self):
        """Test sending unhandled event without MASTER_CHAT_ID configured."""
        with patch("core.utils.github.settings") as mock_settings:
            mock_settings.MASTER_CHAT_ID = None
            result = await send_unhandled_event_to_master(
                event_type="unknown",
                headers={"X-GitHub-Event": "unknown"},
                body={"action": "test"},
            )
            # Should return False if MASTER_CHAT_ID is not set
            assert result is False

    @pytest.mark.unit
    def test_github_utils_module_imports(self):
        """Test that GitHub utils module can be imported."""
        from core import utils

        assert hasattr(utils, "github")
        assert send_unhandled_event_to_master is not None

    @pytest.mark.unit
    def test_send_unhandled_event_is_async(self):
        """Test that send_unhandled_event_to_master is an async function."""
        import inspect

        assert inspect.iscoroutinefunction(send_unhandled_event_to_master)
