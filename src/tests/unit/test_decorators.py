import sys
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.decorators import distributed_lock


class TestDistributedLock:
    """Test distributed_lock decorator."""

    @pytest.mark.async_
    async def test_distributed_lock_decorator(self):
        """Test that distributed_lock decorator works with async functions."""

        @distributed_lock("test_lock")
        async def test_function():
            return "success"

        result = await test_function()
        assert result == "success"

    @pytest.mark.async_
    async def test_distributed_lock_preserves_function_metadata(self):
        """Test that decorator preserves function metadata."""

        @distributed_lock("test_lock_3")
        async def documented_function():
            """This is a documented function."""
            return "result"

        # Check that function still has its name and docstring
        assert documented_function.__name__ == "documented_function"

    @pytest.mark.unit
    def test_distributed_lock_is_callable(self):
        """Test that distributed_lock decorator is callable."""
        from core.decorators import distributed_lock as lock_decorator

        assert callable(lock_decorator)
