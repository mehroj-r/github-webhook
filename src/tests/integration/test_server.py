import sys
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestServerSetup:
    """Test FastAPI server setup."""

    @pytest.mark.unit
    def test_server_module_imports(self):
        """Test that server module can be imported."""
        from core import server

        assert server is not None
        assert hasattr(server, "start_fastapi_server")

    @pytest.mark.unit
    def test_fastapi_app_creation(self):
        """Test that FastAPI app can be created."""
        from fastapi import FastAPI

        app = FastAPI(title="Test App")
        assert app is not None
        assert app.title == "Test App"

    @pytest.mark.async_
    async def test_server_configuration(self):
        """Test server can be configured."""
        from config import settings

        assert settings.HOST is not None
        assert settings.PORT is not None
        assert isinstance(settings.PORT, int)
