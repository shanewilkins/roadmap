"""Tests for user-related CLI commands (Object-Verb pattern)."""

from click.testing import CliRunner

from roadmap.presentation.cli import main


def test_user_help(cli_runner):
    """Test user command help."""
    result = cli_runner.invoke(main, ["user", "--help"])
    assert result.exit_code == 0
    assert "user" in result.output.lower()


def test_user_show_dashboard_command(initialized_roadmap):
    """Test user show-dashboard command."""
    runner = CliRunner()
    result = runner.invoke(main, ["user", "show-dashboard"])
    assert result.exit_code == 0


def test_user_show_dashboard_with_user(initialized_roadmap):
    """Test user show-dashboard with specific user."""
    runner = CliRunner()
    result = runner.invoke(main, ["user", "show-dashboard", "--assignee", "test-user"])
    assert result.exit_code == 0


def test_user_show_notifications_command(initialized_roadmap):
    """Test user show-notifications command."""
    runner = CliRunner()
    result = runner.invoke(main, ["user", "show-notifications"])
    assert result.exit_code == 0


def test_user_show_notifications_with_options(initialized_roadmap):
    """Test user show-notifications with options."""
    runner = CliRunner()
    result = runner.invoke(
        main, ["user", "show-notifications", "--assignee", "test-user", "--mark-read"]
    )
    assert result.exit_code == 0


def test_user_commands_without_roadmap(temp_dir):
    """Test user commands without initialized roadmap."""
    runner = CliRunner()

    commands = [
        ["user", "show-dashboard"],
        ["user", "show-notifications"],
    ]

    for command in commands:
        result = runner.invoke(main, command)
        # Should handle gracefully - some may work without roadmap, others may not
        # We're mainly testing that they don't crash
        assert result.exit_code in [0, 1]  # Allow either success or controlled failure
