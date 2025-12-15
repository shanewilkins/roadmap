"""Tests for issue-related CLI commands."""

from click.testing import CliRunner

from roadmap.adapters.cli import main


def test_issue_help(cli_runner):
    """Test issue command help."""
    result = cli_runner.invoke(main, ["issue", "--help"])
    assert result.exit_code == 0
    assert "Manage issues" in result.output


def test_issue_create_command(cli_runner):
    """Test creating an issue."""
    with cli_runner.isolated_filesystem():
        # Initialize roadmap first
        init_result = cli_runner.invoke(
            main, ["init", "-y", "--skip-github", "--skip-project"]
        )
        assert init_result.exit_code == 0

        result = cli_runner.invoke(main, ["issue", "create", "test-issue"])
        assert result.exit_code == 0


def test_issue_create_without_roadmap(cli_runner):
    """Test creating issue - verifies proper error when not initialized."""
    with cli_runner.isolated_filesystem():
        # Don't initialize roadmap
        result = cli_runner.invoke(main, ["issue", "create", "test-issue"])
        # Should fail gracefully
        assert result.exit_code != 0
        assert "Roadmap not initialized" in result.output


def test_issue_list_command(cli_runner):
    """Test listing issues."""
    with cli_runner.isolated_filesystem():
        # Initialize first
        init_result = cli_runner.invoke(main, ["init", "-y", "--skip-github", "--skip-project"])
        assert init_result.exit_code == 0
        
        result = cli_runner.invoke(main, ["issue", "list"])
        assert result.exit_code == 0


def test_issue_list_without_roadmap(cli_runner):
    """Test listing issues without initialized roadmap."""
    with cli_runner.isolated_filesystem():
        # Don't initialize roadmap
        result = cli_runner.invoke(main, ["issue", "list"])
        # Should fail gracefully
        assert result.exit_code != 0
    # Current implementation requires initialized roadmap
    assert "❌ Roadmap not initialized" in result.output
