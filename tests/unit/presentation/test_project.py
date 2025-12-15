"""Tests for project-related CLI commands."""

from click.testing import CliRunner

from roadmap.adapters.cli import main


def test_project_help(cli_runner):
    """Test project command help."""
    result = cli_runner.invoke(main, ["project", "--help"])
    assert result.exit_code == 0
    assert "project" in result.output.lower()


def test_project_create_command(cli_runner):
    """Test project create command."""
    with cli_runner.isolated_filesystem():
        # Initialize roadmap first
        init_result = cli_runner.invoke(main, ["init", "-y", "--skip-github", "--skip-project"])
        assert init_result.exit_code == 0
        
        result = cli_runner.invoke(main, ["project", "create", "test-project"])
        assert result.exit_code == 0


def test_project_list_command(cli_runner):
    """Test project list command."""
    with cli_runner.isolated_filesystem():
        # Initialize roadmap first
        init_result = cli_runner.invoke(main, ["init", "-y", "--skip-github", "--skip-project"])
        assert init_result.exit_code == 0
        
        result = cli_runner.invoke(main, ["project", "list"])
        assert result.exit_code == 0
        # Should handle gracefully with current implementation
