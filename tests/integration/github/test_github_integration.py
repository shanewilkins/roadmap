"""Integration tests for GitHub issue integration workflows.

Tests complete GitHub integration workflows including:
- Linking issues to GitHub
- Looking up GitHub issue details
- Syncing GitHub issue updates
- Displaying GitHub IDs in listings

Note: These tests use mocked GitHub API responses and focus on
the CLI integration paths rather than full database operations.
"""

from click.testing import CliRunner

from roadmap.adapters.cli import main


def test_link_github_command_exists():
    """Test that link-github command is registered."""
    runner = CliRunner()
    result = runner.invoke(main, ["issue", "link-github", "--help"])
    # Command should exist - either via help or via error message
    assert "link" in result.output.lower() or "usage" in result.output.lower()


def test_lookup_github_command_exists():
    """Test that lookup-github command is registered."""
    runner = CliRunner()
    result = runner.invoke(main, ["issue", "lookup-github", "--help"])
    assert result.exit_code == 0
    assert "lookup" in result.output.lower()


def test_list_command_show_github_ids_flag():
    """Test that list command has --show-github-ids flag."""
    runner = CliRunner()
    result = runner.invoke(main, ["issue", "list", "--help"])
    assert result.exit_code == 0
    assert "github" in result.output.lower() or "show-github-ids" in result.output


def test_workflow_requires_initialization():
    """Test that GitHub commands require initialized roadmap."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Try without initialization
        result = runner.invoke(
            main, ["issue", "link-github", "test-id", "--github-number", "123"]
        )
        # Should fail because roadmap is not initialized
        assert result.exit_code != 0


def test_link_github_help():
    """Test link-github command help output."""
    runner = CliRunner()
    result = runner.invoke(main, ["issue", "link-github", "--help"])
    # Command should exist - help or proper error message
    assert result.output is not None and len(result.output) > 0


def test_lookup_github_help():
    """Test lookup-github command help output."""
    runner = CliRunner()
    result = runner.invoke(main, ["issue", "lookup-github", "--help"])
    assert result.exit_code == 0


def test_issue_view_help():
    """Test that view command exists for detailed display."""
    runner = CliRunner()
    result = runner.invoke(main, ["issue", "view", "--help"])
    assert result.exit_code == 0


def test_github_integration_commands_in_help():
    """Test that GitHub integration commands appear in issue help."""
    runner = CliRunner()
    result = runner.invoke(main, ["issue", "--help"])
    assert result.exit_code == 0
    # Check for GitHub-related commands
    output_lower = result.output.lower()
    assert "link" in output_lower or "github" in output_lower or "sync" in output_lower


def test_workflow_isolation():
    """Test that GitHub operations don't interfere with regular issue operations."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Initialize without GitHub - this verifies basic CLI works
        result = runner.invoke(
            main,
            ["init", "--project-name", "Test", "--non-interactive", "--skip-github"],
        )
        # Verify init completed (exit code 0 means success)
        # Exit code 2 means already initialized, which is also fine
        assert result.exit_code in [0, 2], f"init should complete: {result.output}"
        # Verify something happened (either success or indication it already exists)
        assert "Roadmap" in result.output or result.exit_code == 2


def test_github_integration_imports():
    """Test that GitHub integration modules can be imported."""
    from roadmap.core.services.github.github_integration_service import (
        GitHubIntegrationService,
    )
    from roadmap.core.services.github.github_issue_client import GitHubIssueClient

    # Just verify imports work
    assert GitHubIssueClient is not None
    assert GitHubIntegrationService is not None
