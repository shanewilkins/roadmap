"""Integration tests for CLI commands.

Tests CLI commands end-to-end with proper database and file system isolation.
Uses Click's CliRunner for testing CLI interactions.
"""

import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from roadmap.cli import main


@pytest.fixture
def cli_runner():
    """Provide a Click CLI runner for testing."""
    return CliRunner()


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


@pytest.fixture
def isolated_roadmap_with_issues(isolated_roadmap):
    """Create an isolated roadmap with sample issues.

    Yields:
        tuple: (cli_runner, temp_dir_path, created_issue_ids)
    """
    cli_runner, temp_dir = isolated_roadmap

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
        assert result.exit_code == 0, f"Issue creation failed: {result.output}"
        # Parse the issue ID from the output (format: "ID: <id>")
        import re

        match = re.search(r"ID:\s+([^\s]+)", result.output)
        if match:
            created_ids.append(match.group(1))

    yield cli_runner, temp_dir, created_ids


class TestCLIInit:
    """Test init command."""

    def test_init_non_interactive(self, cli_runner):
        """Test initializing roadmap non-interactively."""
        with cli_runner.isolated_filesystem():
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

            assert result.exit_code == 0
            assert ".roadmap" in os.listdir(".")
            assert (
                "initialized" in result.output.lower()
                or "success" in result.output.lower()
            )

    def test_init_with_description(self, cli_runner):
        """Test init with project description."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(
                main,
                [
                    "init",
                    "--project-name",
                    "Test",
                    "--description",
                    "Test project",
                    "--non-interactive",
                    "--skip-github",
                ],
            )

            assert result.exit_code == 0

    def test_init_creates_database(self, cli_runner):
        """Test that init creates the database file."""
        with cli_runner.isolated_filesystem():
            cli_runner.invoke(
                main,
                [
                    "init",
                    "--project-name",
                    "Test",
                    "--non-interactive",
                    "--skip-github",
                ],
            )

            roadmap_dir = Path(".roadmap")
            assert roadmap_dir.exists()
            # Database should be created (check for .db file or state directory)
            db_files = list(roadmap_dir.glob("*.db"))
            assert len(db_files) > 0 or (roadmap_dir / "state").exists()

    def test_init_help(self, cli_runner):
        """Test init help command."""
        result = cli_runner.invoke(main, ["init", "--help"])

        assert result.exit_code == 0
        assert "init" in result.output.lower()
        assert "project" in result.output.lower()


class TestCLIStatus:
    """Test status command."""

    def test_status_without_init(self, cli_runner):
        """Test status command before initialization."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(main, ["status"])

            # Should handle gracefully - either show not initialized or exit with error
            assert "not initialized" in result.output.lower() or result.exit_code != 0

    def test_status_after_init(self, isolated_roadmap):
        """Test status command after initialization."""
        cli_runner, temp_dir = isolated_roadmap

        result = cli_runner.invoke(main, ["status"])

        assert result.exit_code == 0
        # Status should show roadmap status and issue/milestone info
        assert "roadmap" in result.output.lower() or "status" in result.output.lower()

    def test_status_help(self, cli_runner):
        """Test status help command."""
        result = cli_runner.invoke(main, ["status", "--help"])

        assert result.exit_code == 0
        assert "status" in result.output.lower()


class TestCLIHealth:
    """Test health command."""

    def test_health_check(self, cli_runner):
        """Test health check command."""
        result = cli_runner.invoke(main, ["health"])

        assert result.exit_code == 0
        # Health should report status
        assert (
            "health" in result.output.lower()
            or "status" in result.output.lower()
            or "ok" in result.output.lower()
        )

    def test_health_help(self, cli_runner):
        """Test health help command."""
        result = cli_runner.invoke(main, ["health", "--help"])

        assert result.exit_code == 0


class TestCLIIssueCreate:
    """Test issue create command."""

    def test_create_issue_minimal(self, isolated_roadmap):
        """Test creating issue with minimal arguments."""
        cli_runner, temp_dir = isolated_roadmap

        result = cli_runner.invoke(
            main,
            ["issue", "create", "Test Issue"],  # TITLE is positional
        )

        assert result.exit_code == 0
        assert "created" in result.output.lower() or "issue" in result.output.lower()

    def test_create_issue_with_all_fields(self, isolated_roadmap):
        """Test creating issue with all fields."""
        cli_runner, temp_dir = isolated_roadmap

        result = cli_runner.invoke(
            main,
            [
                "issue",
                "create",
                "Feature Request",  # TITLE is positional
                "--type",
                "feature",
                "--priority",
                "high",
                "--estimate",
                "4.5",
            ],
        )

        assert result.exit_code == 0

    def test_create_issue_help(self, cli_runner):
        """Test issue create help."""
        result = cli_runner.invoke(main, ["issue", "create", "--help"])

        assert result.exit_code == 0
        assert "create" in result.output.lower()
        assert "title" in result.output.lower()


class TestCLIIssueList:
    """Test issue list command."""

    def test_list_issues(self, isolated_roadmap_with_issues):
        """Test listing all issues."""
        cli_runner, temp_dir, _issue_ids = isolated_roadmap_with_issues

        result = cli_runner.invoke(main, ["issue", "list"])

        assert result.exit_code == 0
        # Should show the created issues
        assert "fix bug" in result.output.lower() or "parser" in result.output.lower()

    def test_list_issues_with_status_filter(self, isolated_roadmap_with_issues):
        """Test listing issues with status filter."""
        cli_runner, temp_dir, _issue_ids = isolated_roadmap_with_issues

        result = cli_runner.invoke(main, ["issue", "list", "--status", "todo"])

        assert result.exit_code == 0

    def test_list_issues_with_priority_filter(self, isolated_roadmap_with_issues):
        """Test listing issues with priority filter."""
        cli_runner, temp_dir, _issue_ids = isolated_roadmap_with_issues

        result = cli_runner.invoke(main, ["issue", "list", "--priority", "high"])

        assert result.exit_code == 0

    def test_list_issues_empty(self, isolated_roadmap):
        """Test listing issues when none exist."""
        cli_runner, temp_dir = isolated_roadmap

        result = cli_runner.invoke(main, ["issue", "list"])

        assert result.exit_code == 0
        # Should handle empty list gracefully
        assert (
            "no issues" in result.output.lower()
            or result.output.strip() == ""
            or "issue" in result.output.lower()
        )

    def test_list_issues_help(self, cli_runner):
        """Test issue list help."""
        result = cli_runner.invoke(main, ["issue", "list", "--help"])

        assert result.exit_code == 0


class TestCLIIssueUpdate:
    """Test issue update command."""

    def test_update_issue_title(self, isolated_roadmap_with_issues):
        """Test updating issue title."""
        cli_runner, temp_dir, _issue_ids = isolated_roadmap_with_issues

        # Update using a known issue number (they're created sequentially)
        result = cli_runner.invoke(
            main,
            ["issue", "update", "1", "--title", "Updated Title"],
        )

        assert result.exit_code == 0 or "updated" in result.output.lower()

    def test_update_issue_priority(self, isolated_roadmap_with_issues):
        """Test updating issue priority."""
        cli_runner, temp_dir, _issue_ids = isolated_roadmap_with_issues

        result = cli_runner.invoke(
            main,
            ["issue", "update", "1", "--priority", "critical"],
        )

        assert result.exit_code == 0

    def test_update_nonexistent_issue(self, isolated_roadmap):
        """Test updating non-existent issue."""
        cli_runner, temp_dir = isolated_roadmap

        result = cli_runner.invoke(
            main,
            ["issue", "update", "999", "--title", "Test"],
        )

        # Should fail gracefully
        assert (
            result.exit_code != 0
            or "not found" in result.output.lower()
            or "error" in result.output.lower()
        )

    def test_update_issue_help(self, cli_runner):
        """Test issue update help."""
        result = cli_runner.invoke(main, ["issue", "update", "--help"])

        assert result.exit_code == 0


class TestCLIIssueDelete:
    """Test issue delete command."""

    def test_delete_issue(self, isolated_roadmap_with_issues):
        """Test deleting an issue."""
        cli_runner, temp_dir, issue_ids = isolated_roadmap_with_issues

        # Skip test if no issues were created
        if not issue_ids:
            pytest.skip("No issues created in fixture")

        # Delete first issue with confirmation
        result = cli_runner.invoke(
            main,
            ["issue", "delete", issue_ids[0]],
            input="y\n",
        )

        assert result.exit_code == 0 or "deleted" in result.output.lower()

    def test_delete_issue_force(self, isolated_roadmap_with_issues):
        """Test force deleting an issue."""
        cli_runner, temp_dir, issue_ids = isolated_roadmap_with_issues

        # Skip test if less than 2 issues were created
        if len(issue_ids) < 2:
            pytest.skip("Not enough issues created in fixture")

        result = cli_runner.invoke(
            main,
            ["issue", "delete", issue_ids[1], "--yes"],  # --yes skips confirmation
        )

        assert result.exit_code == 0 or "deleted" in result.output.lower()

    def test_delete_nonexistent_issue(self, isolated_roadmap):
        """Test deleting non-existent issue."""
        cli_runner, temp_dir = isolated_roadmap

        result = cli_runner.invoke(
            main,
            ["issue", "delete", "999", "--force"],
        )

        # Should fail gracefully
        assert result.exit_code != 0 or "not found" in result.output.lower()

    def test_delete_issue_help(self, cli_runner):
        """Test issue delete help."""
        result = cli_runner.invoke(main, ["issue", "delete", "--help"])

        assert result.exit_code == 0


class TestCLIIssueWorkflow:
    """Test issue workflow commands (start, close, progress)."""

    def test_start_issue(self, isolated_roadmap_with_issues):
        """Test starting work on an issue."""
        cli_runner, temp_dir, _issue_ids = isolated_roadmap_with_issues

        result = cli_runner.invoke(main, ["issue", "start", "1"])

        # Should succeed or show status change
        assert (
            result.exit_code == 0
            or "start" in result.output.lower()
            or "in_progress" in result.output.lower()
        )

    def test_close_issue(self, isolated_roadmap_with_issues):
        """Test closing an issue."""
        cli_runner, temp_dir, _issue_ids = isolated_roadmap_with_issues

        # Start first
        cli_runner.invoke(main, ["issue", "start", "1"])

        # Then close
        result = cli_runner.invoke(main, ["issue", "close", "1"])

        assert (
            result.exit_code == 0
            or "close" in result.output.lower()
            or "closed" in result.output.lower()
        )

    def test_update_progress(self, isolated_roadmap_with_issues):
        """Test updating issue progress."""
        cli_runner, temp_dir, _issue_ids = isolated_roadmap_with_issues

        result = cli_runner.invoke(main, ["issue", "progress", "1", "50"])

        assert result.exit_code == 0 or "progress" in result.output.lower()

    def test_block_issue(self, isolated_roadmap_with_issues):
        """Test blocking an issue."""
        cli_runner, temp_dir, _issue_ids = isolated_roadmap_with_issues

        result = cli_runner.invoke(
            main,
            ["issue", "block", "1", "--reason", "Waiting for dependency"],
        )

        assert result.exit_code == 0 or "block" in result.output.lower()

    def test_unblock_issue(self, isolated_roadmap_with_issues):
        """Test unblocking an issue."""
        cli_runner, temp_dir, _issue_ids = isolated_roadmap_with_issues

        # Block first
        cli_runner.invoke(
            main,
            ["issue", "block", "1", "--reason", "Test"],
        )

        # Then unblock
        result = cli_runner.invoke(main, ["issue", "unblock", "1"])

        assert result.exit_code == 0 or "unblock" in result.output.lower()

    def test_start_issue_help(self, cli_runner):
        """Test start command help."""
        result = cli_runner.invoke(main, ["issue", "start", "--help"])

        assert result.exit_code == 0

    def test_close_issue_help(self, cli_runner):
        """Test close command help."""
        result = cli_runner.invoke(main, ["issue", "close", "--help"])

        assert result.exit_code == 0


class TestCLIIssueHelp:
    """Test issue command help."""

    def test_issue_group_help(self, cli_runner):
        """Test issue group help."""
        result = cli_runner.invoke(main, ["issue", "--help"])

        assert result.exit_code == 0
        assert "issue" in result.output.lower()
        # Should list subcommands
        assert "create" in result.output.lower()
        assert "list" in result.output.lower()

    def test_all_issue_subcommands_have_help(self, cli_runner):
        """Test that all issue subcommands have help."""
        subcommands = [
            "create",
            "list",
            "update",
            "delete",
            "start",
            "close",
            "progress",
            "block",
            "unblock",
            "deps",
        ]

        for cmd in subcommands:
            result = cli_runner.invoke(main, ["issue", cmd, "--help"])
            assert result.exit_code == 0, f"{cmd} help failed"


class TestCLIRootHelp:
    """Test root CLI help."""

    def test_root_help(self, cli_runner):
        """Test root help command."""
        result = cli_runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "roadmap" in result.output.lower()

    def test_no_command_shows_help(self, cli_runner):
        """Test that running without command shows help."""
        result = cli_runner.invoke(main, [])

        # Click may return exit code 0 (help) or 2 (missing command)
        assert result.exit_code in [0, 2]
        assert "roadmap" in result.output.lower() or "usage" in result.output.lower()

    def test_version_flag(self, cli_runner):
        """Test --version flag."""
        result = cli_runner.invoke(main, ["--version"])

        assert result.exit_code == 0
        # Should show version info
        assert "version" in result.output.lower() or len(result.output.strip()) > 0


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

    def test_create_milestone_minimal(self, isolated_roadmap):
        """Test creating milestone with minimal arguments."""
        cli_runner, temp_dir = isolated_roadmap

        result = cli_runner.invoke(
            main,
            ["milestone", "create", "Test Milestone"],
        )

        assert result.exit_code == 0
        assert (
            "created" in result.output.lower() or "milestone" in result.output.lower()
        )

    def test_create_milestone_with_description(self, isolated_roadmap):
        """Test creating milestone with description."""
        cli_runner, temp_dir = isolated_roadmap

        result = cli_runner.invoke(
            main,
            [
                "milestone",
                "create",
                "Sprint 1",
                "--description",
                "First development sprint",
            ],
        )

        assert result.exit_code == 0

    def test_create_milestone_with_due_date(self, isolated_roadmap):
        """Test creating milestone with due date."""
        cli_runner, temp_dir = isolated_roadmap

        result = cli_runner.invoke(
            main,
            [
                "milestone",
                "create",
                "Release 1.0",
                "--due-date",
                "2025-12-31",
            ],
        )

        assert result.exit_code == 0

    def test_create_milestone_help(self, cli_runner):
        """Test milestone create help."""
        result = cli_runner.invoke(main, ["milestone", "create", "--help"])

        assert result.exit_code == 0
        assert "create" in result.output.lower()


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

    def test_list_milestones_help(self, cli_runner):
        """Test milestone list help."""
        result = cli_runner.invoke(main, ["milestone", "list", "--help"])

        assert result.exit_code == 0


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

        # Command exits 0 but shows error message
        assert "failed" in result.output.lower()

    def test_assign_to_nonexistent_milestone(self, isolated_roadmap_with_issues):
        """Test assigning to non-existent milestone."""
        cli_runner, temp_dir, _issue_ids = isolated_roadmap_with_issues

        result = cli_runner.invoke(
            main,
            ["milestone", "assign", "1", "Nonexistent"],
        )

        # Command exits 0 but shows error message
        assert "failed" in result.output.lower()

    def test_assign_help(self, cli_runner):
        """Test milestone assign help."""
        result = cli_runner.invoke(main, ["milestone", "assign", "--help"])

        assert result.exit_code == 0


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

    def test_update_help(self, cli_runner):
        """Test milestone update help."""
        result = cli_runner.invoke(main, ["milestone", "update", "--help"])

        assert result.exit_code == 0


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

        # Command exits 0 but shows error message
        assert "failed" in result.output.lower()

    def test_close_help(self, cli_runner):
        """Test milestone close help."""
        result = cli_runner.invoke(main, ["milestone", "close", "--help"])

        assert result.exit_code == 0


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

    def test_delete_help(self, cli_runner):
        """Test milestone delete help."""
        result = cli_runner.invoke(main, ["milestone", "delete", "--help"])

        assert result.exit_code == 0


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


class TestCLIDataExport:
    """Test data export command."""

    def test_export_json_format(self, isolated_roadmap_with_issues):
        """Test exporting data to JSON format."""
        cli_runner, temp_dir, _issue_ids = isolated_roadmap_with_issues

        output_file = temp_dir / "export.json"
        result = cli_runner.invoke(
            main,
            ["data", "export", "--format", "json", "-o", str(output_file)],
        )

        assert result.exit_code == 0
        assert output_file.exists()
        # Verify it's valid JSON
        import json

        with open(output_file) as f:
            data = json.load(f)
            assert isinstance(data, list | dict)

    def test_export_csv_format(self, isolated_roadmap_with_issues):
        """Test exporting data to CSV format."""
        cli_runner, temp_dir, _issue_ids = isolated_roadmap_with_issues

        output_file = temp_dir / "export.csv"
        result = cli_runner.invoke(
            main,
            ["data", "export", "--format", "csv", "-o", str(output_file)],
        )

        assert result.exit_code == 0
        assert output_file.exists()
        # Verify CSV has content
        content = output_file.read_text()
        assert len(content) > 0

    def test_export_markdown_format(self, isolated_roadmap_with_issues):
        """Test exporting data to Markdown format."""
        cli_runner, temp_dir, _issue_ids = isolated_roadmap_with_issues

        output_file = temp_dir / "export.md"
        result = cli_runner.invoke(
            main,
            ["data", "export", "--format", "markdown", "-o", str(output_file)],
        )

        assert result.exit_code == 0
        assert output_file.exists()
        # Verify markdown has content
        content = output_file.read_text()
        assert len(content) > 0

    def test_export_without_output_file(self, isolated_roadmap_with_issues):
        """Test export outputs to stdout when no file specified."""
        cli_runner, temp_dir, _issue_ids = isolated_roadmap_with_issues

        result = cli_runner.invoke(
            main,
            ["data", "export", "--format", "json"],
        )

        assert result.exit_code == 0
        # Should have output
        assert len(result.output) > 0

    def test_export_with_filter(self, isolated_roadmap_with_issues):
        """Test export with filter option."""
        cli_runner, temp_dir, _issue_ids = isolated_roadmap_with_issues

        output_file = temp_dir / "filtered.json"
        result = cli_runner.invoke(
            main,
            [
                "data",
                "export",
                "--format",
                "json",
                "-o",
                str(output_file),
                "--filter",
                "status=open",
            ],
        )

        # Command should succeed even if no matching data
        assert result.exit_code == 0

    def test_export_help(self, cli_runner):
        """Test data export help."""
        result = cli_runner.invoke(main, ["data", "export", "--help"])

        assert result.exit_code == 0
        assert "export" in result.output.lower()


class TestCLIDataGroup:
    """Test data command group."""

    def test_data_group_help(self, cli_runner):
        """Test data group help."""
        result = cli_runner.invoke(main, ["data", "--help"])

        assert result.exit_code == 0
        assert "export" in result.output.lower()


class TestCLIGitIntegration:
    """Test git integration commands."""

    @pytest.fixture
    def isolated_git_repo(self, isolated_roadmap_with_issues):
        """Create an isolated roadmap with git repo."""
        cli_runner, temp_dir, _issue_ids = isolated_roadmap_with_issues

        # Initialize git repo
        import subprocess

        subprocess.run(["git", "init"], cwd=temp_dir, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=temp_dir,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=temp_dir,
            check=True,
            capture_output=True,
        )
        # Initial commit
        subprocess.run(
            ["git", "add", "."], cwd=temp_dir, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=temp_dir,
            check=True,
            capture_output=True,
        )

        return cli_runner, temp_dir

    def test_git_status(self, isolated_git_repo):
        """Test git status command."""
        cli_runner, temp_dir = isolated_git_repo

        result = cli_runner.invoke(main, ["git", "status"])

        assert result.exit_code == 0
        # Should show git information
        assert len(result.output) > 0

    def test_git_status_without_repo(self, isolated_roadmap_with_issues):
        """Test git status without git repo."""
        cli_runner, temp_dir, _issue_ids = isolated_roadmap_with_issues

        result = cli_runner.invoke(main, ["git", "status"])

        # Should handle gracefully (exit 0 or show error message)
        assert result.exit_code == 0 or "not a git repository" in result.output.lower()

    def test_git_branch_create(self, isolated_git_repo):
        """Test creating git branch for issue."""
        cli_runner, temp_dir = isolated_git_repo

        result = cli_runner.invoke(
            main,
            ["git", "branch", "1", "--no-checkout"],
        )

        # Should create branch
        assert result.exit_code == 0 or "branch" in result.output.lower()

    def test_git_branch_with_checkout(self, isolated_git_repo):
        """Test creating and checking out git branch."""
        cli_runner, temp_dir = isolated_git_repo

        result = cli_runner.invoke(
            main,
            ["git", "branch", "1", "--checkout"],
        )

        # Should create and checkout branch
        assert result.exit_code == 0 or "branch" in result.output.lower()

    def test_git_branch_nonexistent_issue(self, isolated_git_repo):
        """Test creating branch for nonexistent issue."""
        cli_runner, temp_dir = isolated_git_repo

        result = cli_runner.invoke(
            main,
            ["git", "branch", "999"],
        )

        # Should fail gracefully
        assert (
            result.exit_code != 0
            or "not found" in result.output.lower()
            or "failed" in result.output.lower()
        )

    def test_git_branch_help(self, cli_runner):
        """Test git branch help."""
        result = cli_runner.invoke(main, ["git", "branch", "--help"])

        assert result.exit_code == 0
        assert "branch" in result.output.lower()

    def test_git_status_help(self, cli_runner):
        """Test git status help."""
        result = cli_runner.invoke(main, ["git", "status", "--help"])

        assert result.exit_code == 0


class TestCLIGitGroup:
    """Test git command group."""

    def test_git_group_help(self, cli_runner):
        """Test git group help."""
        result = cli_runner.invoke(main, ["git", "--help"])

        assert result.exit_code == 0
        assert "status" in result.output.lower()
        assert "branch" in result.output.lower()

    def test_all_git_subcommands_have_help(self, cli_runner):
        """Test that all git subcommands have help."""
        subcommands = ["status", "branch", "setup", "link", "sync"]

        for cmd in subcommands:
            result = cli_runner.invoke(main, ["git", cmd, "--help"])
            assert result.exit_code == 0, f"{cmd} help failed"
