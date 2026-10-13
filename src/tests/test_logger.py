import json
import logging
import sys
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core import get_logger


class TestLogger:
    """Test logger functionality."""

    @pytest.mark.unit
    def test_get_logger_returns_logger(self):
        """Test that get_logger returns a logging.Logger instance."""
        logger = get_logger(__name__)
        assert isinstance(logger, logging.Logger)

    @pytest.mark.unit
    def test_get_logger_with_different_names(self):
        """Test that get_logger creates loggers with correct names."""
        logger1 = get_logger("test.module1")
        logger2 = get_logger("test.module2")

        assert logger1.name == "test.module1"
        assert logger2.name == "test.module2"

    @pytest.mark.unit
    def test_get_logger_cached(self):
        """Test that same logger is returned for same module name."""
        logger1 = get_logger("test.module")
        logger2 = get_logger("test.module")

        assert logger1 is logger2


def _record(msg: str = "hello %s", args: tuple = ("world",), **extra) -> logging.LogRecord:
    record = logging.LogRecord("app.test", logging.INFO, __file__, 1, msg, args, None)
    record.__dict__.update(extra)
    return record


class TestStructuredLogging:
    @pytest.mark.unit
    def test_json_formatter_emits_one_object_with_extras(self):
        from core.utils.logger import JsonFormatter

        entry = json.loads(JsonFormatter().format(_record(repo_name="octocat/Hello-World", delivery_id="d-1")))

        assert entry["message"] == "hello world"
        assert entry["level"] == "INFO"
        assert entry["logger"] == "app.test"
        assert entry["repo_name"] == "octocat/Hello-World"
        assert entry["delivery_id"] == "d-1"
        assert "args" not in entry
        assert "msg" not in entry

    @pytest.mark.unit
    def test_json_formatter_includes_exception(self):
        from core.utils.logger import JsonFormatter

        try:
            raise ValueError("bad")
        except ValueError:
            record = _record()
            record.exc_info = sys.exc_info()

        entry = json.loads(JsonFormatter().format(record))
        assert "ValueError: bad" in entry["exc_info"]

    @pytest.mark.unit
    def test_context_filter_copies_delivery_id(self):
        from core.utils.logger import ContextFilter, delivery_id_var

        token = delivery_id_var.set("abc-123")
        try:
            record = _record()
            assert ContextFilter().filter(record) is True
        finally:
            delivery_id_var.reset(token)

        assert record.delivery_id == "abc-123"

    @pytest.mark.unit
    def test_context_filter_defaults_to_none_outside_a_delivery(self):
        from core.utils.logger import ContextFilter

        record = _record()
        ContextFilter().filter(record)
        assert record.delivery_id is None

    @pytest.mark.unit
    def test_every_handler_has_the_context_filter(self):
        from core.utils.logger import LOGGING_CONFIG

        assert all(h.get("filters") == ["context"] for h in LOGGING_CONFIG["handlers"].values())
