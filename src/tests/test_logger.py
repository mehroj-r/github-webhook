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
