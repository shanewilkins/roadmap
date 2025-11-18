"""Tests for team-related CLI commands (Object-Verb pattern)."""

from click.testing import CliRunner

from roadmap.presentation.cli import main


def test_team_help(cli_runner):
    """Test team command help."""
    result = cli_runner.invoke(main, ["team", "--help"])
    assert result.exit_code == 0
    assert "team" in result.output.lower()


def test_team_forecast_capacity_command(initialized_roadmap):
    """Test team forecast-capacity command."""
    runner = CliRunner()
    result = runner.invoke(main, ["team", "forecast-capacity"])
    assert result.exit_code == 0
    # Should handle the case where no issues exist gracefully


def test_team_forecast_capacity_with_options(initialized_roadmap):
    """Test team forecast-capacity with options."""
    runner = CliRunner()
    result = runner.invoke(
        main, ["team", "forecast-capacity", "--days", "14", "--assignee", "test-user"]
    )
    assert result.exit_code == 0


def test_team_analyze_workload_command(initialized_roadmap):
    """Test team analyze-workload command."""
    runner = CliRunner()
    result = runner.invoke(main, ["team", "analyze-workload"])
    assert result.exit_code == 0


def test_team_assign_smart_command(initialized_roadmap):
    """Test team assign-smart command."""
    runner = CliRunner()

    # Create an issue first
    issue_result = runner.invoke(main, ["issue", "create", "test-issue"])

    # Extract issue ID
    issue_id = None
    for line in issue_result.output.split("\n"):
        if "ID:" in line:
            issue_id = line.split(":")[1].strip()
            break

    if issue_id:
        result = runner.invoke(main, ["team", "assign-smart", issue_id])
        assert result.exit_code == 0


def test_team_broadcast_command(initialized_roadmap):
    """Test team broadcast command."""
    runner = CliRunner()
    result = runner.invoke(main, ["team", "broadcast", "Test message"])
    assert result.exit_code == 0


def test_team_show_activity_command(initialized_roadmap):
    """Test team show-activity command."""
    runner = CliRunner()
    result = runner.invoke(main, ["team", "show-activity"])
    assert result.exit_code == 0


def test_team_handoff_command(initialized_roadmap):
    """Test team handoff command."""
    runner = CliRunner()
    result = runner.invoke(main, ["team", "handoff", "old-user", "new-user"])
    assert result.exit_code == 0


def test_team_commands_without_roadmap(temp_dir):
    """Test team commands without initialized roadmap."""
    runner = CliRunner()

    commands = [
        ["team", "forecast-capacity"],
        ["team", "analyze-workload"],
        ["team", "show-activity"],
    ]

    for command in commands:
        result = runner.invoke(main, command)
        # Should handle gracefully - some may work without roadmap, others may not
        # We're mainly testing that they don't crash
        assert result.exit_code in [0, 1]  # Allow either success or controlled failure
