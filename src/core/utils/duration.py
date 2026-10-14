"""Parse human-friendly durations such as '30m', '2h', '1d12h'."""

import re
from datetime import timedelta

_UNITS = {"m": 60, "h": 3600, "d": 86400, "w": 604800}
_PATTERN = re.compile(r"(\d+)([mhdw])")


def parse_duration(text: str) -> timedelta | None:
    """Return a timedelta for inputs like '45m', '2h', '1d6h'; None when the text is not a duration."""
    text = text.strip().lower()
    if not text or _PATTERN.sub("", text):
        return None

    seconds = sum(int(amount) * _UNITS[unit] for amount, unit in _PATTERN.findall(text))
    return timedelta(seconds=seconds) if seconds > 0 else None


def format_duration(delta: timedelta) -> str:
    """Render a timedelta compactly, e.g. '1d 2h 5m'."""
    total = int(delta.total_seconds())
    if total <= 0:
        return "0m"
    parts = []
    for unit, size in (("d", 86400), ("h", 3600), ("m", 60)):
        amount, total = divmod(total, size)
        if amount:
            parts.append(f"{amount}{unit}")
    return " ".join(parts) or "<1m"
