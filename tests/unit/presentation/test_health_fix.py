"""Integration tests for health fix CLI command."""

import click

from roadmap.bootstrap import cli as main


class TestHealthFixCommand:
    """Integration tests for 'roadmap health fix' command."""

    def test_command_registered(self):
        """Test that health fix command is registered in the CLI."""
        # The main CLI group should have the health subcommand
        assert main.get_command(click.Context(main), "health") is not None
