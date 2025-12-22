"""Tests for CLI validators."""

from roadmap.adapters.cli.cli_validators import validate_priority


class TestValidatePriority:
    """Test validate_priority function."""

    def test_validate_priority_function_exists(self):
        """Test that validate_priority function is available."""
        assert callable(validate_priority)

    def test_validate_priority_returns_priority_or_none(self):
        """Test that validate_priority returns Priority or None."""
        # Test with an invalid value
        result = validate_priority("invalid")
        assert result is None
