import sys
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import handlers.github  # noqa: F401
from core.decorators import GitHubEventRegistry
from core.enums import GHEventType


class TestGitHubEventRegistry:
    @pytest.mark.unit
    def test_every_github_event_has_registered_handler(self):
        for event in GHEventType:
            handler = GitHubEventRegistry.get_handler(event=event)
            assert handler is not None, f"No handler registered for {event.value}"

    @pytest.mark.unit
    def test_every_github_event_has_registered_model(self):
        for event in GHEventType:
            model = GitHubEventRegistry.get_event_model(event=event)
            assert model is not None, f"No model registered for {event.value}"
