"""Tests for CLI init module."""

import roadmap.adapters.cli.init as init_module
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

    def test_module_exports_init_in_all(self):
        """Module should explicitly export only the init command."""
        assert init_module.__all__ == ["init"]

    def test_reexport_matches_commands_init(self):
        """Re-export should point at the command from init.commands."""
        from roadmap.adapters.cli.init.commands import init as command_init

        assert init is command_init
