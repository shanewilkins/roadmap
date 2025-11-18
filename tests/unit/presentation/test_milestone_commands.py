"""Tests for milestone CLI commands."""

import pytest
from click.testing import CliRunner

from roadmap.cli import main
from tests.unit.shared.test_utils import strip_ansi


@pytest.fixture
def initialized_roadmap(temp_dir):
    """Create a temporary directory with initialized roadmap."""
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "init",
            "--non-interactive",
            "--skip-github",
            "--project-name",
            "Test Project",
        ],
    )
    assert result.exit_code == 0
    return temp_dir


def test_milestone_create_command(initialized_roadmap):
    """Test creating a milestone."""
    runner = CliRunner()

    result = runner.invoke(
        main, ["milestone", "create", "v1.0", "--description", "First release"]
    )
    assert result.exit_code == 0
    assert "✅ Created milestone: v1.0" in strip_ansi(result.output)


def test_milestone_create_command_with_due_date(initialized_roadmap):
    """Test creating a milestone with description only."""
    runner = CliRunner()

    result = runner.invoke(
        main, ["milestone", "create", "v1.0", "--description", "First release"]
    )
    assert result.exit_code == 0
    assert "✅ Created milestone: v1.0" in strip_ansi(result.output)


def test_milestone_create_command_invalid_date(initialized_roadmap):
    """Test creating a milestone without description."""
    runner = CliRunner()

    result = runner.invoke(main, ["milestone", "create", "v1.0"])
    assert result.exit_code == 0
    assert "✅ Created milestone: v1.0" in strip_ansi(result.output)


def test_milestone_create_command_without_roadmap(temp_dir):
    """Test creating a milestone without initialized roadmap."""
    runner = CliRunner()

    result = runner.invoke(main, ["milestone", "create", "v1.0"])
    assert result.exit_code == 0
    assert "❌ Roadmap not initialized" in result.output


def test_milestone_list_command(initialized_roadmap):
    """Test listing milestones."""
    runner = CliRunner()

    # Create some milestones first
    runner.invoke(
        main, ["milestone", "create", "v1.0", "--description", "First release"]
    )
    runner.invoke(
        main, ["milestone", "create", "v2.0", "--description", "Second release"]
    )

    result = runner.invoke(main, ["milestone", "list"])
    assert result.exit_code == 0
    clean_output = strip_ansi(result.output)
    assert "v1.0" in clean_output
    assert "v2.0" in clean_output


def test_milestone_list_command_empty(initialized_roadmap):
    """Test listing milestones when none exist."""
    runner = CliRunner()

    result = runner.invoke(main, ["milestone", "list"])
    assert result.exit_code == 0
    assert "No milestones found" in result.output


def test_milestone_list_command_without_roadmap(temp_dir):
    """Test listing milestones without initialized roadmap."""
    runner = CliRunner()

    result = runner.invoke(main, ["milestone", "list"])
    assert result.exit_code == 0
    assert "❌ Roadmap not initialized" in result.output


def test_milestone_assign_command(initialized_roadmap):
    """Test assigning an issue to a milestone."""
    runner = CliRunner()

    # Create a milestone and an issue
    runner.invoke(
        main, ["milestone", "create", "v1.0", "--description", "First release"]
    )
    result = runner.invoke(main, ["issue", "create", "test-issue"])

    # Extract issue ID
    output_lines = result.output.split("\n")
    id_line = [line for line in output_lines if "ID:" in line][0]
    issue_id = id_line.split("ID:")[1].strip()

    # Assign issue to milestone (correct order: issue_id milestone_name)
    result = runner.invoke(main, ["milestone", "assign", issue_id, "v1.0"])
    assert result.exit_code == 0
    # Check that the assignment was successful using the dynamic issue ID
    assert f"✅ Assigned issue {issue_id} to milestone 'v1.0'" in strip_ansi(
        result.output
    )


def test_milestone_assign_command_nonexistent_milestone(
    initialized_roadmap, strip_ansi_fixture
):
    """Test assigning an issue to a non-existent milestone."""
    runner = CliRunner()

    # Create an issue
    result = runner.invoke(main, ["issue", "create", "test-issue"])
    output_lines = result.output.split("\n")
    id_line = [line for line in output_lines if "ID:" in line][0]
    issue_id = id_line.split("ID:")[1].strip()

    # Try to assign to non-existent milestone
    result = runner.invoke(main, ["milestone", "assign", issue_id, "nonexistent"])
    assert result.exit_code == 0
    # Check for the actual error message format
    clean_output = strip_ansi_fixture(result.output)
    assert "❌ Failed to assign" in clean_output and "nonexistent" in clean_output


def test_milestone_assign_command_nonexistent_issue(
    initialized_roadmap, strip_ansi_fixture
):
    """Test assigning a non-existent issue to a milestone."""
    runner = CliRunner()

    # Create a milestone
    runner.invoke(
        main, ["milestone", "create", "v1.0", "--description", "First release"]
    )

    # Try to assign non-existent issue
    result = runner.invoke(main, ["milestone", "assign", "nonexistent", "v1.0"])
    assert result.exit_code == 0
    # Check for the actual error message format
    clean_output = strip_ansi_fixture(result.output)
    assert "❌ Failed to assign" in clean_output and "nonexistent" in clean_output


def test_milestone_assign_command_without_roadmap(temp_dir):
    """Test assigning an issue to a milestone without initialized roadmap."""
    runner = CliRunner()

    result = runner.invoke(main, ["milestone", "assign", "some-id", "v1.0"])
    assert result.exit_code == 0
    assert "❌ Roadmap not initialized" in result.output


def test_milestone_delete_command(initialized_roadmap):
    """Test deleting a milestone."""
    runner = CliRunner()

    # Create a milestone
    runner.invoke(
        main, ["milestone", "create", "v1.0", "--description", "First release"]
    )

    # Delete it (needs confirmation)
    result = runner.invoke(main, ["milestone", "delete", "v1.0"], input="y\n")
    assert result.exit_code == 0
    # Check for the actual success message format
    assert "✅ Deleted milestone: v1.0" in strip_ansi(result.output)


def test_milestone_delete_command_nonexistent(initialized_roadmap, strip_ansi_fixture):
    """Test deleting a non-existent milestone."""
    runner = CliRunner()

    result = runner.invoke(main, ["milestone", "delete", "nonexistent"], input="y\n")
    assert result.exit_code == 0
    clean_output = strip_ansi_fixture(result.output)
    assert "❌ Milestone not found: nonexistent" in clean_output


def test_milestone_delete_command_without_roadmap(temp_dir):
    """Test deleting a milestone without initialized roadmap."""
    runner = CliRunner()

    result = runner.invoke(main, ["milestone", "delete", "v1.0"], input="y\n")
    assert result.exit_code == 0
    assert "❌ Roadmap not initialized" in result.output
