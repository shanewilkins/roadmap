"""Tests for CLI utils module."""

from roadmap.adapters.cli.console_exports import get_console, is_testing_environment


class TestCliUtils:
    """Test CLI utility functions."""

    def test_get_console_imported(self):
        """Test that get_console is available."""
        assert callable(get_console)

    def test_is_testing_environment_imported(self):
        """Test that is_testing_environment is available."""
        assert callable(is_testing_environment)

    def test_get_console_returns_console(self):
        """Test that get_console returns a console object."""
        console = get_console()
        assert console is not None

    def test_is_testing_environment_returns_bool(self):
        """Test that is_testing_environment returns a boolean."""
        result = is_testing_environment()
        assert isinstance(result, bool)

    def test_is_testing_environment_true_in_tests(self):
        """Test that is_testing_environment returns True during testing."""
        # This test runs in the test environment
        result = is_testing_environment()
        assert result
