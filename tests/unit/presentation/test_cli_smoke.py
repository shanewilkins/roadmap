"""Smoke tests for CLI command availability and help output."""

import pytest

from roadmap.adapters.cli import main


class TestCliSmoke:
    """Smoke tests for CLI command availability."""

    @pytest.mark.parametrize(
        "cmd",
        [
            "--help",
            "data",
            "init",
            "issue",
            "milestone",
            "project",
            "status",
        ],
    )
    def test_command_help(self, cli_runner, cmd):
        """Ensure top-level commands print help and exit correctly."""
        args = [] if cmd == "--help" else [cmd, "--help"]
        result = cli_runner.invoke(main, args)
        # In Click 8.1+, both root --help and subcommand help exit with 0
        # This changed from older Click versions which used exit code 2 for root help
        assert result.exit_code == 0

    def test_data_export_help(self, cli_runner):
        """Test that data export command has help available."""
        result = cli_runner.invoke(main, ["data", "export", "--help"])
        assert result.exit_code == 0

    def test_git_group_help(self, cli_runner):
        """Test that git command group has help available."""
        result = cli_runner.invoke(main, ["git", "--help"])
        assert result.exit_code == 0
