import sys
from datetime import timedelta
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.utils.duration import format_duration, parse_duration


class TestDuration:
    @pytest.mark.unit
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("30m", timedelta(minutes=30)),
            ("2h", timedelta(hours=2)),
            ("1d6h", timedelta(days=1, hours=6)),
            ("1w", timedelta(weeks=1)),
            (" 45M ", timedelta(minutes=45)),
        ],
    )
    def test_parse_valid(self, text, expected):
        assert parse_duration(text) == expected

    @pytest.mark.unit
    @pytest.mark.parametrize("text", ["", "abc", "0m", "5", "2 h", "1x"])
    def test_parse_invalid(self, text):
        assert parse_duration(text) is None

    @pytest.mark.unit
    def test_format(self):
        assert format_duration(timedelta(days=1, hours=2, minutes=5)) == "1d 2h 5m"
        assert format_duration(timedelta(seconds=10)) == "<1m"
        assert format_duration(timedelta(0)) == "0m"
