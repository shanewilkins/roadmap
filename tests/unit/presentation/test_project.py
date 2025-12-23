"""Tests for project-related CLI commands."""

import pytest
from click.testing import CliRunner

from roadmap.adapters.cli import main


@pytest.fixture
def cli_runner():
    """Provide a Click test runner."""
    return CliRunner()


class TestProjectCommand:
    """Test project-related CLI commands."""

    def test_project_help(self, cli_runner):
        """Test project command help."""
        result = cli_runner.invoke(main, ["project", "--help"])
        assert result.exit_code == 0
        assert "project" in result.output.lower()

    def test_project_subcommands(self, cli_runner):
        """Test project subcommands work with initialized roadmap."""
        with cli_runner.isolated_filesystem():
            # Initialize roadmap first
            init_result = cli_runner.invoke(
                main, ["init", "-y", "--skip-github", "--skip-project"]
            )
            assert init_result.exit_code == 0

            # Test create command
            create_result = cli_runner.invoke(
                main, ["project", "create", "test-project"]
            )
            assert create_result.exit_code == 0

            # Test list command
            list_result = cli_runner.invoke(main, ["project", "list"])
            assert list_result.exit_code == 0

