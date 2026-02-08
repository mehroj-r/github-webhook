import sys
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.utils.command_validator import BaseCommandValidator


class TestCommandValidator:
    """Test command validation functionality."""

    @pytest.mark.unit
    def test_base_command_validator_initialization(self):
        """Test BaseCommandValidator can be initialized."""
        validator = BaseCommandValidator()
        assert validator is not None
        assert hasattr(validator, "arguments")
        assert hasattr(validator, "error_msg")

    @pytest.mark.async_
    async def test_validate_length_with_matching_args(self):
        """Test validate__length with matching argument count."""

        class TestValidator(BaseCommandValidator):
            arguments = ["arg1", "arg2"]

        validator = TestValidator()
        result, msg = await validator.validate__length({"arg1": "value1", "arg2": "value2"})
        assert result is True
        assert msg == ""

    @pytest.mark.async_
    async def test_validate_length_with_mismatched_args(self):
        """Test validate__length with mismatched argument count."""

        class TestValidator(BaseCommandValidator):
            arguments = ["arg1", "arg2"]
            error_msg = "Invalid number of arguments"

        validator = TestValidator()
        result, msg = await validator.validate__length({"arg1": "value1"})
        assert result is False
        assert msg == "Invalid number of arguments"

    @pytest.mark.unit
    def test_base_validator_has_validate_method(self):
        """Test that BaseCommandValidator has validate method."""
        validator = BaseCommandValidator()
        assert hasattr(validator, "validate")
        assert callable(validator.validate)
