import sys
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.notifications import compact_text

VERBOSE = (
    "🚀 <b>Push to repo</b>\n"
    "🌿 Branch: main\n"
    "👤 Pusher: alice\n"
    "📝 2 commits\n\n"
    "  • <a href='u'>first</a>\n"
    "  • <a href='u'>second</a>\n"
    "<blockquote>Some body\nwith lines</blockquote>\n"
    "• Detail: <code>x</code>"
)


class TestCompactText:
    @pytest.mark.unit
    def test_drops_quotes_lists_and_blank_lines(self):
        compact = compact_text(VERBOSE)
        assert compact == "🚀 <b>Push to repo</b>\n🌿 Branch: main\n👤 Pusher: alice\n📝 2 commits"

    @pytest.mark.unit
    def test_headline_only_message_is_unchanged(self):
        text = "<b>Issue opened</b> in repo\n🔖 #1 title"
        assert compact_text(text) == text


class TestRenderFor:
    @pytest.mark.unit
    def test_compact_keeps_first_link_and_all_actions(self):
        from unittest.mock import MagicMock

        from core.notifications import render_for

        target = MagicMock()
        target.chat.is_compact = True
        buttons = [("View", "https://a"), ("Files", "https://b"), ("Approve", "callback:gh:x"), ("Merge", "callback:gh:y")]

        _, rendered = render_for(target, "<b>t</b>", buttons)

        assert rendered == [("View", "https://a"), ("Approve", "callback:gh:x"), ("Merge", "callback:gh:y")]
