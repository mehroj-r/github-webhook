import sys
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import _get_settings, settings


class TestSettings:
    """Test Settings configuration."""

    @pytest.mark.unit
    def test_settings_instance(self):
        """Test that settings instance is created."""
        assert settings is not None

    @pytest.mark.unit
    def test_settings_cached(self):
        """Test that settings are cached with lru_cache."""
        settings1 = _get_settings()
        settings2 = _get_settings()
        assert settings1 is settings2

    @pytest.mark.unit
    def test_settings_has_required_attributes(self):
        """Test that settings has all required attributes."""
        required_attrs = [
            "APP_NAME",
            "DEBUG",
            "BOT_TOKEN",
            "USE_WEBHOOK",
            "HOST",
            "PORT",
            "DATABASE_URL",
        ]
        for attr in required_attrs:
            assert hasattr(settings, attr)

    @pytest.mark.unit
    def test_default_settings_values(self):
        """Test default settings values."""
        assert settings.APP_NAME == "Github Webhook Bot"
        assert settings.HOST == "0.0.0.0"
        assert settings.PORT == 8000
        assert settings.WEBHOOK_PATH == "/webhook"
        assert settings.GH_WEBHOOK_PATH == "/webhook"
