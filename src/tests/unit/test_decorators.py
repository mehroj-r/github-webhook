import sys
import zlib
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.decorators import distributed_lock, parse_command


def _mock_session_maker(lock_result: bool):
    """Build an async_session_maker stub whose session returns lock_result for pg_try_advisory_lock."""
    session = AsyncMock()
    execute_result = MagicMock()
    execute_result.scalar.return_value = lock_result
    session.execute.return_value = execute_result

    maker = MagicMock()
    maker.return_value.__aenter__ = AsyncMock(return_value=session)
    maker.return_value.__aexit__ = AsyncMock(return_value=False)
    return maker, session


class TestDistributedLock:
    """Test distributed_lock decorator."""

    @pytest.mark.async_
    async def test_distributed_lock_decorator(self):
        """Test that the function runs and the lock is released when acquired."""
        maker, session = _mock_session_maker(lock_result=True)

        with patch("core.decorators.async_session_maker", maker):

            @distributed_lock("test_lock")
            async def test_function():
                return "success"

            result = await test_function()

        assert result == "success"
        assert session.execute.await_count == 2  # lock + unlock

    @pytest.mark.async_
    async def test_distributed_lock_skips_when_held(self):
        """Test that the function is skipped when another worker holds the lock."""
        maker, session = _mock_session_maker(lock_result=False)
        called = False

        with patch("core.decorators.async_session_maker", maker):

            @distributed_lock("test_lock_2")
            async def test_function():
                nonlocal called
                called = True

            result = await test_function()

        assert result is None
        assert called is False
        assert session.execute.await_count == 1  # no unlock

    @pytest.mark.async_
    async def test_distributed_lock_id_is_stable_across_processes(self):
        """The lock id must not depend on the process-salted hash()."""
        maker, session = _mock_session_maker(lock_result=True)

        with patch("core.decorators.async_session_maker", maker):

            @distributed_lock("telegram_webhook_init")
            async def test_function():
                return None

            await test_function()

        expected = zlib.crc32(b"telegram_webhook_init") % (2**31)
        _, params = session.execute.await_args_list[0].args
        assert params == {"lock_id": expected}

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


class TestParseCommand:
    """Test parse_command decorator."""

    @staticmethod
    def _validator(valid: bool = True, error: str = "bad"):
        validator = MagicMock()
        validator.error_msg = "usage"
        validator.validate = AsyncMock(return_value=(valid, "" if valid else error))
        return validator

    @pytest.mark.async_
    async def test_parse_command_tolerates_repeated_whitespace(self):
        """Multiple spaces between command and argument must not produce empty arguments."""
        validator = self._validator()
        message = MagicMock()
        message.text = "/connect_repo    https://github.com/a/b  "
        message.reply = AsyncMock()

        @parse_command(arguments=["repo_url"], validator=validator)
        async def handler(message, repo_url: str):
            return repo_url

        assert await handler(message) == "https://github.com/a/b"
        validator.validate.assert_awaited_once_with(args_data={"repo_url": "https://github.com/a/b"})
        message.reply.assert_not_called()

    @pytest.mark.async_
    async def test_parse_command_replies_with_validation_error(self):
        """Validation failures are reported to the user and the handler is not called."""
        validator = self._validator(valid=False, error="Invalid GitHub repository URL.")
        message = MagicMock()
        message.text = "/connect_repo nope"
        message.reply = AsyncMock()
        called = False

        @parse_command(arguments=["repo_url"], validator=validator)
        async def handler(message, repo_url: str):
            nonlocal called
            called = True

        assert await handler(message) is None
        assert called is False
        message.reply.assert_awaited_once_with("Invalid GitHub repository URL.")
