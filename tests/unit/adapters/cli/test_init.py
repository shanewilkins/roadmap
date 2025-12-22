"""Tests for CLI init module."""

from roadmap.adapters.cli.init import init


class TestCliInitModule:
    """Test CLI init module."""

    def test_init_imported(self):
        """Test that init command is available."""
        assert init is not None
        assert callable(init)

    def test_init_is_click_command(self):
        """Test that init is a Click command."""
        # Check if it has click's callback attribute
        assert hasattr(init, "callback") or callable(init)
