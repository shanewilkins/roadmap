"""Smoke tests for CLI command availability and help output."""

import pytest
from click.testing import CliRunner

from roadmap.adapters.cli import main


@pytest.fixture
def cli_runner():
    """Provide a Click test runner."""
    return CliRunner()


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
        # Root --help exits with 2; subcommand help exits with 0
        expected_exit = 2 if cmd == "--help" else 0
        assert result.exit_code == expected_exit

    def test_data_export_help(self, cli_runner):
        """Test that data export command has help available."""
        result = cli_runner.invoke(main, ["data", "export", "--help"])
        assert result.exit_code == 0

    def test_git_group_help(self, cli_runner):
        """Test that git command group has help available."""
        result = cli_runner.invoke(main, ["git", "--help"])
        assert result.exit_code == 0
