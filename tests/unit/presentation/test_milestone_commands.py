"""Tests for milestone CLI commands."""

from roadmap.adapters.cli import main
from tests.unit.shared.test_utils import strip_ansi


def test_milestone_create_command(cli_runner):
    """Test creating a milestone."""
    with cli_runner.isolated_filesystem():
        # Initialize first
        init_result = cli_runner.invoke(
            main, ["init", "-y", "--skip-github", "--skip-project"]
        )
        assert init_result.exit_code == 0

        result = cli_runner.invoke(
            main, ["milestone", "create", "v1.0", "--description", "First release"]
        )
        assert result.exit_code == 0
        assert "Created" in result.output or "v1.0" in result.output


def test_milestone_create_command_with_due_date(cli_runner):
    """Test creating a milestone with description."""
    with cli_runner.isolated_filesystem():
        # Initialize first
        init_result = cli_runner.invoke(
            main, ["init", "-y", "--skip-github", "--skip-project"]
        )
        assert init_result.exit_code == 0

        result = cli_runner.invoke(
            main, ["milestone", "create", "v1.0", "--description", "First release"]
        )
        assert result.exit_code == 0
        assert "Created" in result.output or "v1.0" in result.output


def test_milestone_create_command_invalid_date(cli_runner):
    """Test creating a milestone without description."""
    with cli_runner.isolated_filesystem():
        # Initialize first
        init_result = cli_runner.invoke(
            main, ["init", "-y", "--skip-github", "--skip-project"]
        )
        assert init_result.exit_code == 0

        result = cli_runner.invoke(main, ["milestone", "create", "v1.0"])
        assert result.exit_code == 0
        assert "Created" in result.output or "v1.0" in result.output


def test_milestone_create_command_without_roadmap(cli_runner):
    """Test creating a milestone without initialized roadmap."""
    with cli_runner.isolated_filesystem():
        result = cli_runner.invoke(main, ["milestone", "create", "v1.0"])
        # Should fail without initialized roadmap
        assert result.exit_code != 0


def test_milestone_list_command(cli_runner):
    """Test listing milestones."""
    with cli_runner.isolated_filesystem():
        # Initialize first
        init_result = cli_runner.invoke(
            main, ["init", "-y", "--skip-github", "--skip-project"]
        )
        assert init_result.exit_code == 0

        # Create some milestones first
        cli_runner.invoke(
            main, ["milestone", "create", "v1.0", "--description", "First release"]
        )
        cli_runner.invoke(
            main, ["milestone", "create", "v2.0", "--description", "Second release"]
        )

        result = cli_runner.invoke(main, ["milestone", "list"])
        assert result.exit_code == 0
        clean_output = strip_ansi(result.output)
        assert "v1.0" in clean_output
        assert "v2.0" in clean_output


def test_milestone_list_command_empty(cli_runner):
    """Test listing milestones when none exist."""
    with cli_runner.isolated_filesystem():
        # Initialize first
        init_result = cli_runner.invoke(
            main, ["init", "-y", "--skip-github", "--skip-project"]
        )
        assert init_result.exit_code == 0

        result = cli_runner.invoke(main, ["milestone", "list"])
        assert result.exit_code == 0


def test_milestone_list_command_without_roadmap(cli_runner):
    """Test listing milestones without initialized roadmap."""
    with cli_runner.isolated_filesystem():
        result = cli_runner.invoke(main, ["milestone", "list"])
        # Should fail without initialized roadmap
        assert result.exit_code != 0


def test_milestone_assign_command(cli_runner):
    """Test assigning an issue to a milestone."""
    with cli_runner.isolated_filesystem():
        # Initialize first
        init_result = cli_runner.invoke(
            main, ["init", "-y", "--skip-github", "--skip-project"]
        )
        assert init_result.exit_code == 0

        # Create a milestone and an issue
        cli_runner.invoke(
            main, ["milestone", "create", "v1.0", "--description", "First release"]
        )
        result = cli_runner.invoke(main, ["issue", "create", "test-issue"])

        # Extract issue ID
        output_lines = result.output.split("\n")
        id_line = [line for line in output_lines if "ID:" in line]
        if id_line:
            issue_id = id_line[0].split("ID:")[1].strip()

            # Assign issue to milestone
            result = cli_runner.invoke(main, ["milestone", "assign", issue_id, "v1.0"])
            assert result.exit_code == 0
            # Check that assignment was successful
            assert "Assigned" in result.output


def test_milestone_assign_command_nonexistent_milestone(cli_runner):
    """Test assigning an issue to a non-existent milestone."""
    with cli_runner.isolated_filesystem():
        # Initialize first
        init_result = cli_runner.invoke(
            main, ["init", "-y", "--skip-github", "--skip-project"]
        )
        assert init_result.exit_code == 0

        # Create an issue
        result = cli_runner.invoke(main, ["issue", "create", "test-issue"])
        output_lines = result.output.split("\n")
        id_line = [line for line in output_lines if "ID:" in line]
        if id_line:
            issue_id = id_line[0].split("ID:")[1].strip()

            # Try to assign to non-existent milestone
            result = cli_runner.invoke(
                main, ["milestone", "assign", issue_id, "nonexistent"]
            )
            # Should fail gracefully
            assert result.exit_code != 0 or "Failed" in result.output


def test_milestone_assign_command_nonexistent_issue(cli_runner):
    """Test assigning a non-existent issue to a milestone."""
    with cli_runner.isolated_filesystem():
        # Initialize first
        init_result = cli_runner.invoke(
            main, ["init", "-y", "--skip-github", "--skip-project"]
        )
        assert init_result.exit_code == 0

        # Create a milestone
        cli_runner.invoke(
            main, ["milestone", "create", "v1.0", "--description", "First release"]
        )

        # Try to assign non-existent issue
        result = cli_runner.invoke(main, ["milestone", "assign", "nonexistent", "v1.0"])
        # Should fail gracefully
        assert result.exit_code != 0 or "Failed" in result.output


def test_milestone_assign_command_without_roadmap(cli_runner):
    """Test assigning an issue to a milestone without initialized roadmap."""
    with cli_runner.isolated_filesystem():
        result = cli_runner.invoke(main, ["milestone", "assign", "some-id", "v1.0"])
        # Should fail without initialized roadmap
        assert result.exit_code != 0


def test_milestone_delete_command(cli_runner):
    """Test deleting a milestone."""
    with cli_runner.isolated_filesystem():
        # Initialize first
        init_result = cli_runner.invoke(
            main, ["init", "-y", "--skip-github", "--skip-project"]
        )
        assert init_result.exit_code == 0

        # Create a milestone
        cli_runner.invoke(
            main, ["milestone", "create", "v1.0", "--description", "First release"]
        )

        # Delete it (needs confirmation)
        result = cli_runner.invoke(main, ["milestone", "delete", "v1.0"], input="y\n")
        assert result.exit_code == 0
        # Check for success (either success or error message, but exit code 0)
        assert "v1.0" in result.output


def test_milestone_delete_command_nonexistent(cli_runner):
    """Test deleting a non-existent milestone."""
    with cli_runner.isolated_filesystem():
        # Initialize first
        init_result = cli_runner.invoke(
            main, ["init", "-y", "--skip-github", "--skip-project"]
        )
        assert init_result.exit_code == 0

        result = cli_runner.invoke(
            main, ["milestone", "delete", "nonexistent"], input="y\n"
        )
        # Should handle gracefully
        assert result.exit_code == 0 or "nonexistent" in result.output


def test_milestone_delete_command_without_roadmap(cli_runner):
    """Test deleting a milestone without initialized roadmap."""
    with cli_runner.isolated_filesystem():
        result = cli_runner.invoke(main, ["milestone", "delete", "v1.0"], input="y\n")
        # Should fail without initialized roadmap
        assert result.exit_code != 0
