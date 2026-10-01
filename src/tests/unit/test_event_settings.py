import sys
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database.models import GithubRepository
from handlers.github.catalog import DEFAULT_ENABLED_EVENTS, EVENT_KEYS, OTHER_EVENTS_KEY, event_key


class TestEventCatalog:
    @pytest.mark.unit
    def test_defaults_are_listed_keys(self):
        assert DEFAULT_ENABLED_EVENTS <= set(EVENT_KEYS)

    @pytest.mark.unit
    def test_unlisted_events_map_to_other(self):
        assert event_key("push") == "push"
        assert event_key("gollum") == OTHER_EVENTS_KEY

    @pytest.mark.unit
    def test_callback_data_fits_telegram_limit(self):
        from uuid import uuid4

        from handlers.bot.keyboards import events_callback

        assert all(len(events_callback(uuid4(), i)) <= 64 for i in range(len(EVENT_KEYS)))


class TestRepositoryEventSettings:
    @pytest.mark.unit
    def test_defaults_when_unset(self):
        repo = GithubRepository(title="o/r", url="https://github.com/o/r")
        assert repo.is_event_enabled("push") is True
        assert repo.is_event_enabled("star") is False
        assert repo.is_event_enabled("gollum") is False

    @pytest.mark.unit
    def test_toggle_returns_new_list(self):
        repo = GithubRepository(title="o/r", url="https://github.com/o/r")
        toggled = repo.toggled_events("push")
        assert "push" not in toggled
        assert repo.enabled_events is None  # not persisted by toggled_events

        repo.enabled_events = toggled
        assert repo.is_event_enabled("push") is False
        assert "star" in repo.toggled_events("star")

    @pytest.mark.unit
    def test_other_toggle_controls_unlisted_events(self):
        repo = GithubRepository(title="o/r", url="https://github.com/o/r", enabled_events=[OTHER_EVENTS_KEY])
        assert repo.is_event_enabled("gollum") is True
        assert repo.is_event_enabled("push") is False
