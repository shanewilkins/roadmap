"""Integration tests for CLI commands.

Integration tests for CLI milestone commands.

Uses Click's CliRunner for testing CLI interactions.
"""

from pathlib import Path

import pytest

from roadmap.adapters.cli import main


@pytest.fixture
def isolated_roadmap(cli_runner):
    """Create an isolated roadmap environment with initialized database.

    Yields:
        tuple: (cli_runner, temp_dir_path)
    """
    with cli_runner.isolated_filesystem():
        temp_dir = Path.cwd()

        # Initialize a roadmap in this directory
        result = cli_runner.invoke(
            main,
            [
                "init",
                "--project-name",
                "Test Project",
                "--non-interactive",
                "--skip-github",
            ],
        )

        assert result.exit_code == 0, f"Init failed: {result.output}"

        yield cli_runner, temp_dir
        # Cleanup happens here when context exits


@pytest.fixture
def isolated_roadmap_with_issues(cli_runner):
    """Create an isolated roadmap with sample issues.

    Yields:
        tuple: (cli_runner, temp_dir_path, created_issue_ids)
    """
    with cli_runner.isolated_filesystem():
        temp_dir = Path.cwd()

        # Initialize a roadmap in this directory
        result = cli_runner.invoke(
            main,
            [
                "init",
                "--project-name",
                "Test Project",
                "--non-interactive",
                "--skip-github",
            ],
        )
        assert result.exit_code == 0, f"Init failed: {result.output}"

        # Create a few test issues
        issues = [
            {"title": "Fix bug in parser", "type": "bug", "priority": "high"},
            {"title": "Add new feature", "type": "feature", "priority": "medium"},
            {"title": "Update documentation", "type": "other", "priority": "low"},
        ]

        created_ids = []
        for issue in issues:
            result = cli_runner.invoke(
                main,
                [
                    "issue",
                    "create",
                    issue["title"],  # TITLE is positional argument
                    "--type",
                    issue["type"],
                    "--priority",
                    issue["priority"],
                ],
            )
            if result.exit_code == 0:
                # Parse the issue ID from the output
                from tests.fixtures.click_testing import ClickTestHelper

                try:
                    issue_id = ClickTestHelper.extract_issue_id(result.output)
                    created_ids.append(issue_id)
                except ValueError:
                    # If extraction fails, continue without the ID
                    pass

        yield cli_runner, temp_dir, created_ids
        # Cleanup happens here when context exits


@pytest.fixture
def isolated_roadmap_with_milestone(isolated_roadmap_with_issues):
    """Create an isolated roadmap with issues and a milestone.

    Yields:
        tuple: (cli_runner, temp_dir_path)
    """
    cli_runner, temp_dir, _issue_ids = isolated_roadmap_with_issues

    # Create a milestone
    result = cli_runner.invoke(
        main,
        ["milestone", "create", "Sprint 1", "--description", "First sprint"],
    )
    assert result.exit_code == 0, f"Milestone creation failed: {result.output}"

    yield cli_runner, temp_dir


class TestCLIMilestoneCreate:
    """Test milestone create command."""

    @pytest.mark.parametrize(
        "name,options",
        [
            ("Test Milestone", []),  # Minimal
            (
                "Sprint 1",
                ["--description", "First development sprint"],
            ),  # With description
            ("Release 1.0", ["--due-date", "2025-12-31"]),  # With due date
        ],
    )
    def test_create_milestone(self, isolated_roadmap, name, options):
        """Test creating milestones with various options."""
        cli_runner, temp_dir = isolated_roadmap

        result = cli_runner.invoke(
            main,
            ["milestone", "create", name] + options,
        )

        assert result.exit_code == 0
        assert (
            "created" in result.output.lower() or "milestone" in result.output.lower()
        )


class TestCLIMilestoneList:
    """Test milestone list command."""

    def test_list_milestones(self, isolated_roadmap_with_milestone):
        """Test listing all milestones."""
        cli_runner, temp_dir = isolated_roadmap_with_milestone

        result = cli_runner.invoke(main, ["milestone", "list"])

        assert result.exit_code == 0
        # Should show the created milestone
        assert "sprint" in result.output.lower() or "milestone" in result.output.lower()

    def test_list_milestones_empty(self, isolated_roadmap):
        """Test listing milestones when none exist."""
        cli_runner, temp_dir = isolated_roadmap

        result = cli_runner.invoke(main, ["milestone", "list"])

        assert result.exit_code == 0
        # Should handle empty list gracefully


class TestCLIMilestoneAssign:
    """Test milestone assign command."""

    def test_assign_issue_to_milestone(self, isolated_roadmap_with_milestone):
        """Test assigning an issue to a milestone."""
        cli_runner, temp_dir = isolated_roadmap_with_milestone

        result = cli_runner.invoke(
            main,
            ["milestone", "assign", "1", "Sprint 1"],
        )

        assert result.exit_code == 0 or "assigned" in result.output.lower()

    def test_assign_nonexistent_issue(self, isolated_roadmap_with_milestone):
        """Test assigning non-existent issue."""
        cli_runner, temp_dir = isolated_roadmap_with_milestone

        result = cli_runner.invoke(
            main,
            ["milestone", "assign", "999", "Sprint 1"],
        )

        # Should either exit with error or show error message
        assert result.exit_code != 0 or "failed" in result.output.lower()

    def test_assign_to_nonexistent_milestone(self, isolated_roadmap_with_issues):
        """Test assigning to non-existent milestone."""
        cli_runner, temp_dir, _issue_ids = isolated_roadmap_with_issues

        result = cli_runner.invoke(
            main,
            ["milestone", "assign", "1", "Nonexistent"],
        )

        # Should either exit with error or show error message
        assert result.exit_code != 0 or "failed" in result.output.lower()


class TestCLIMilestoneUpdate:
    """Test milestone update command."""

    def test_update_milestone_description(self, isolated_roadmap_with_milestone):
        """Test updating milestone description."""
        cli_runner, temp_dir = isolated_roadmap_with_milestone

        result = cli_runner.invoke(
            main,
            ["milestone", "update", "Sprint 1", "--description", "Updated description"],
        )

        assert result.exit_code == 0 or "updated" in result.output.lower()

    def test_update_nonexistent_milestone(self, isolated_roadmap):
        """Test updating non-existent milestone."""
        cli_runner, temp_dir = isolated_roadmap

        result = cli_runner.invoke(
            main,
            ["milestone", "update", "Nonexistent", "--description", "Test"],
        )

        # Should fail gracefully
        assert (
            result.exit_code != 0
            or "not found" in result.output.lower()
            or "error" in result.output.lower()
        )


class TestCLIMilestoneClose:
    """Test milestone close command."""

    def test_close_milestone(self, isolated_roadmap_with_milestone):
        """Test closing a milestone."""
        cli_runner, temp_dir = isolated_roadmap_with_milestone

        result = cli_runner.invoke(
            main,
            ["milestone", "close", "Sprint 1"],
        )

        assert (
            result.exit_code == 0
            or "close" in result.output.lower()
            or "completed" in result.output.lower()
        )

    def test_close_nonexistent_milestone(self, isolated_roadmap):
        """Test closing non-existent milestone."""
        cli_runner, temp_dir = isolated_roadmap

        result = cli_runner.invoke(
            main,
            ["milestone", "close", "Nonexistent"],
        )

        # Should either exit with error or show error message
        assert result.exit_code != 0 or "failed" in result.output.lower()


class TestCLIMilestoneDelete:
    """Test milestone delete command."""

    def test_delete_milestone(self, isolated_roadmap_with_milestone):
        """Test deleting a milestone."""
        cli_runner, temp_dir = isolated_roadmap_with_milestone

        # Create an extra milestone to delete
        cli_runner.invoke(main, ["milestone", "create", "To Delete"])

        result = cli_runner.invoke(
            main,
            ["milestone", "delete", "To Delete"],
            input="y\n",
        )

        assert result.exit_code == 0 or "deleted" in result.output.lower()

    def test_delete_nonexistent_milestone(self, isolated_roadmap):
        """Test deleting non-existent milestone."""
        cli_runner, temp_dir = isolated_roadmap

        result = cli_runner.invoke(
            main,
            ["milestone", "delete", "Nonexistent"],
            input="y\n",
        )

        # Should fail gracefully
        assert (
            result.exit_code != 0
            or "not found" in result.output.lower()
            or "error" in result.output.lower()
        )


class TestCLIMilestoneHelp:
    """Test milestone command help."""

    def test_milestone_group_help(self, cli_runner):
        """Test milestone group help."""
        result = cli_runner.invoke(main, ["milestone", "--help"])

        assert result.exit_code == 0
        assert "milestone" in result.output.lower()
        # Should list subcommands
        assert "create" in result.output.lower()
        assert "list" in result.output.lower()

    def test_all_milestone_subcommands_have_help(self, cli_runner):
        """Test that all milestone subcommands have help."""
        subcommands = [
            "create",
            "list",
            "assign",
            "update",
            "delete",
            "close",
            "recalculate",
            "kanban",
        ]

        for cmd in subcommands:
            result = cli_runner.invoke(main, ["milestone", cmd, "--help"])
            assert result.exit_code == 0, f"{cmd} help failed"
