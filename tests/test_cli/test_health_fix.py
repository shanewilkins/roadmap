"""Integration tests for health fix CLI command."""

from roadmap.adapters.cli import main


class TestHealthFixCommand:
    """Integration tests for 'roadmap health fix' command."""

    def test_command_registered(self):
        """Test that health fix command is registered in the CLI."""
        # The main CLI group should have the health subcommand
        assert hasattr(main, "commands")
        assert "health" in main.commands
